from io import BytesIO


def render_invoice_pdf(invoice, business):
    """Render a PDF strictly from the stored Invoice/InvoiceItem snapshot.

    Never reads the live Product/Customer/Sale records: an issued invoice's PDF
    must stay identical even after those change (BR-12).
    """
    # Imported lazily so the rest of the app (migrations, unrelated views, the
    # test suite) never depends on reportlab being installed to load.
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 20 * mm
    right = width - 20 * mm
    y = height - 20 * mm

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(left, y, business.name or "Business")
    y -= 7 * mm

    pdf.setFont("Helvetica", 10)
    contact = " | ".join(bit for bit in (business.phone, business.address, business.city) if bit)
    if contact:
        pdf.drawString(left, y, contact)
        y -= 10 * mm
    else:
        y -= 4 * mm

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(left, y, f"Invoice {invoice.invoice_number}")
    y -= 7 * mm

    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, y, f"Issued: {timezone_str(invoice.issued_at)}")
    y -= 6 * mm
    pdf.drawString(left, y, f"Status: {invoice.status}")
    y -= 10 * mm

    pdf.drawString(left, y, f"Customer: {invoice.customer_name or '-'}")
    y -= 6 * mm
    pdf.drawString(left, y, f"Phone: {invoice.customer_phone or '-'}")
    y -= 10 * mm

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(left, y, "Product")
    pdf.drawRightString(left + 90 * mm, y, "Qty")
    pdf.drawRightString(left + 130 * mm, y, "Unit price")
    pdf.drawRightString(right, y, "Line total")
    y -= 2 * mm
    pdf.line(left, y, right, y)
    y -= 6 * mm

    pdf.setFont("Helvetica", 10)
    for item in invoice.items.all():
        if y < 30 * mm:
            pdf.showPage()
            y = height - 20 * mm
            pdf.setFont("Helvetica", 10)

        pdf.drawString(left, y, item.product_name[:45])
        pdf.drawRightString(left + 90 * mm, y, str(item.quantity))
        pdf.drawRightString(left + 130 * mm, y, f"{item.unit_price:.2f}")
        pdf.drawRightString(right, y, f"{item.line_total:.2f}")
        y -= 6 * mm

    y -= 4 * mm
    pdf.line(left, y, right, y)
    y -= 8 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(right, y, f"Total: {invoice.total:.2f}")
    y -= 12 * mm

    if invoice.notes:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(left, y, f"Notes: {invoice.notes}")

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def timezone_str(value):
    return value.strftime("%Y-%m-%d %H:%M UTC")
