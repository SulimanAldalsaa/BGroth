# BGroth API Reference (for the Android / Kotlin team)

Derived from the backend source and **verified by calling the running API** and by the automated test suite
(`python manage.py test`, 211 tests as of Sprint 3 Phase 4). Where behaviour is a bug or a gap it is flagged
with ⚠️ — see [`GAP_REPORT.md`](GAP_REPORT.md) for the pre-Sprint-3 list (invoices, debts, reports and the
profile update it describes as missing are now implemented; everything else in it is still accurate).

Base URL: see the README (`http://10.0.2.2:8000/` from the emulator). All bodies are JSON
(`Content-Type: application/json`).

## Conventions

| Topic | Behaviour |
|---|---|
| Auth header | `Authorization: Bearer <access_token>` on everything except register, login, token refresh, password-reset |
| IDs | integers, except `User.id` which is a UUID string |
| Money / decimals | JSON **strings** with 2 decimals, e.g. `"2.50"` (including the dashboard). Send them as strings or numbers |
| Dates | `datetime` = ISO-8601 UTC (`2026-09-20T15:03:13.042807Z`); `expense_date` = `YYYY-MM-DD` |
| Lists | Plain JSON array by default. Search, ordering, date filters and opt-in pagination are described in [List query parameters](#list-query-parameters) |
| Business required | Every `/api/business/*` endpoint except `POST /api/business/` returns `404 {"detail": "Business not found. Please create a business first."}` until the user creates a business |

### List query parameters

| Endpoint | `search` | `ordering` (prefix `-` = descending) | Default order | Date filters | Pagination |
|---|---|---|---|---|---|
| `GET /products/` | `name` (contains, case-insensitive) | `name`, `selling_price`, `quantity`, `created_at` | `name` | – | – |
| `GET /customers/` | `name` (contains, case-insensitive) | `name`, `created_at` | `name` | – | – |
| `GET /sales/` | – | `sold_at`, `total_amount`, `paid_amount` | `-sold_at` | `date_from`, `date_to` | `page`, `page_size` |
| `GET /expenses/` | – | `expense_date`, `amount`, `created_at` | `-expense_date` | `date_from`, `date_to` | `page`, `page_size` |
| `GET /invoices/` | – | `issued_at`, `total` | `-issued_at` | `date_from`, `date_to` (on `issued_at`) | `page`, `page_size` |
| `GET /debts/` | `party_name` (contains, case-insensitive) | `due_date`, `original_amount`, `created_at` | `-created_at` | `due_before` (see [Debts](#debts)) | – |

- Parameters combine freely (for example `?category=rent&date_from=2026-09-01&ordering=-amount&page_size=10`).
  Everything is applied to the caller's own business only.
- **Search:** `?search=cola`. Lists that do not support `search` ignore it.
- **Ordering:** `?ordering=-total_amount`. Ties are broken by id, so the order is stable. An unknown field is ignored and the default order is used.
- **Dates:** `date_from` and `date_to` are `YYYY-MM-DD` and **inclusive** (`date_to=2026-09-20` includes the whole of 20 Sep).
  Sales are compared with the date of `sold_at` in the server time zone (UTC); expenses with `expense_date`.
  A blank value (`?date_from=`) is ignored. A malformed date, or `date_from` later than `date_to`, returns
  `400 {"date_from": ["Date has wrong format. Use one of these formats instead: YYYY-MM-DD."]}`
  (or `{"date_to": [...]}`).
- **Pagination (sales and expenses only) is opt-in.** Without `page` / `page_size` the response is the plain array described
  throughout this document. If either parameter is present the response becomes an envelope
  (`page_size` defaults to 20, maximum 100; a page past the end returns `404 {"detail": "Invalid page."}`):

```json
{"count": 42, "next": "http://host/api/business/sales/?page=2&page_size=20", "previous": null,
 "results": [ /* the same objects as in the plain array */ ]}
```

### Error shapes (handle all of them)

```json
{"email": ["User with this email address already exists."]}          // 400 field errors
{"non_field_errors": ["Invalid email or password."]}                  // 400
{"detail": "Insufficient stock for Cola."}                            // 400 business rule / 404 / 401
{"error": "refresh token is required."}                               // 400 (logout only)
{"detail": "Given token not valid for any token type", "code": "token_not_valid", "messages": [...]}  // 401 bad/expired access token
```
Unhandled server errors (500) return an **HTML page**, not JSON. Rate limit hit → `429`.

### Common status codes

| Code | Meaning here |
|---|---|
| 200 / 201 / 204 | OK / created / deleted |
| 400 | Validation or business-rule error. **Also used for wrong login credentials** (not 401) |
| 401 | Missing / invalid / expired access token, or blacklisted refresh token |
| 404 | Object not found, **or belongs to another user**, or user has no business yet |
| 405 | Method not supported (e.g. `PUT /api/business/`, `GET .../payments/`) |
| 429 | Password-reset request throttle (5/hour per IP) |

---

## Authentication

Tokens: access = 30 min, refresh = 14 days, **refresh rotation ON + blacklist**.

### POST `/api/auth/register/` — no auth
Request:
```json
{"email": "user@example.com", "first_name": "Ahmad", "last_name": "Yousef",
 "password": "S3cure!Pass99", "password_confirm": "S3cure!Pass99"}
```
`email`, `password`, `password_confirm` required; `first_name`, `last_name` optional. Password runs Django validators (min 8, not common, not numeric, not similar to user data).

`201`:
```json
{"user": {"id": "uuid", "email": "...", "first_name": "...", "last_name": "...", "full_name": "...",
          "is_active": true, "is_email_verified": false, "date_joined": "ISO"},
 "tokens": {"access": "...", "refresh": "..."}}
```
Errors (400): `{"password": ["This password is too common.", ...]}`, `{"email": ["User with this email address already exists."]}`, `{"password_confirm": ["Passwords do not match."]}`.

### POST `/api/auth/login/` — no auth
Request `{"email": "...", "password": "..."}` → `200` same body as register.
Wrong email/password → **`400`** `{"non_field_errors": ["Invalid email or password."]}`; disabled account → 400 `"This account is disabled."`.

### POST `/api/auth/token/refresh/` — no auth header
Request `{"refresh": "<refresh>"}` → `200 {"access": "...", "refresh": "..."}`.
**Store the new `refresh`**: the old one is blacklisted; reusing it → `401 {"detail": "Token is blacklisted", "code": "token_not_valid"}`.
Expired/invalid refresh → 401. That means the session is over: clear tokens and go to login.

### POST `/api/auth/logout/` — auth required
Request `{"refresh": "<refresh>"}` → `200 {"message": "Logged out successfully."}`.
Missing refresh → `400 {"error": "refresh token is required."}`; invalid → `400 {"error": "Invalid or already expired token."}`.

### GET `/api/auth/me/` — auth required
`200` user object (same as `user` above).

### PATCH `/api/auth/me/` — auth required
Edits the caller's own profile. Only `first_name` and `last_name` are editable — the only two
profile fields the `User` model has beyond identity/account-status fields. Both are optional
(partial update) and accept blank strings.
```json
{"first_name": "Khalid", "last_name": "Hassan"}
```
`200` → the same user object as `GET`. `PUT` is **not** supported (405, same convention as `/api/business/`).

`email` and every other field (`id`, `is_active`, `is_email_verified`, `is_staff`, `date_joined`,
`password`, `full_name`) are protected: including any of them in the request body — even alongside
a valid `first_name`/`last_name` — rejects the **whole** request with `400` and nothing is changed:
```json
{"email": ["This field cannot be edited."]}
```
There is no email-change workflow (only password reset), so `email` cannot be changed at all.
Unauthenticated → `401`.

### POST `/api/auth/change-password/` — auth required
Request `{"old_password", "new_password", "new_password_confirm"}` → `200 {"message": "Password changed successfully."}`.
Errors (400): `{"old_password": ["Old password is incorrect."]}`, `{"new_password_confirm": ["Passwords do not match."]}`, password-validator errors on `new_password`.
Existing tokens stay valid after a password change.

### POST `/api/auth/password-reset/request/` — no auth
Request `{"email": "..."}` → always `200 {"message": "If an account with this email exists, a reset link has been sent."}`. Sends an email whose link is `FRONTEND_RESET_PASSWORD_URL?token=<uuid>`; token valid 60 min, single use. Throttled 5/hour per IP (429).
⚠️ Needs working SMTP; see gap report (500 if SMTP is misconfigured).

### POST `/api/auth/password-reset/confirm/` — no auth
Request `{"token": "<uuid>", "new_password", "new_password_confirm"}` → `200 {"message": "Password has been reset successfully. Please log in."}`.
Errors (400): `{"token": ["Invalid or expired reset link."]}`, `{"token": ["This reset link has expired or was already used."]}`.

---

## Business

### GET `/api/business/` — auth
`200` business, or `404 {"detail": "Business not found."}` (→ show business-setup screen).
```json
{"id": 1, "name": "Shop A", "description": "", "phone": "", "address": "", "city": "Amman",
 "country": "", "created_at": "ISO", "updated_at": "ISO"}
```

### POST `/api/business/` — auth
Request: `name` (required), `description`, `phone`, `address`, `city`, `country` (optional strings). `201` business.
Second attempt → `400 {"non_field_errors": ["You already have a business."]}` (one business per user, BR-2).

### PATCH `/api/business/` — auth
Partial update of the same fields → `200` business. `PUT` is **not** supported (405).

---

## Dashboard

### GET `/api/business/dashboard/` — auth
```json
{
  "today": {"sales": "100.00", "expenses": "30.00", "profit": "70.00"},
  "week":  {"sales": "700.00", "expenses": "200.00", "profit": "500.00"},
  "month": {"sales": "2500.00", "expenses": "800.00", "profit": "1700.00"},
  "sales_today": "100.00", "expenses_today": "30.00", "profit_today": "70.00"
}
```
- `sales` = sum of `total_amount` of the sales in the period (paid or not); `expenses` = sum of expense `amount`;
  `profit = sales − expenses` (can be negative). All values are decimal strings; no data gives `"0.00"`.
- **Periods** are calendar periods, inclusive: `today`; `week` = Monday to Sunday of the current week;
  `month` = 1st to last day of the current month. Sales use the date of `sold_at`, expenses use `expense_date`.
  An expense dated later in the current week/month counts in that period.
- "Today" is computed in the server time zone (`TIME_ZONE = UTC`), not the merchant's local time zone.
- `sales_today`, `expenses_today` and `profit_today` are **deprecated** copies of `today` kept for existing clients.
  New code should read `today.sales`, `today.expenses`, `today.profit`.
- Still not provided: chart series, outstanding debts, inventory / low-stock counts.

---

## Categories

Fields: `id`, `name` (required, unique per business), `description`, `created_at`, `updated_at`.

| Method | Path | Notes |
|---|---|---|
| GET / POST | `/api/business/categories/` | POST 201; duplicate name → `400 {"name": ["This category already exists."]}` |
| GET / PUT / PATCH / DELETE | `/api/business/categories/{id}/` | Deleting a category sets `category = null` on its products |

---

## Products / inventory

Product object:
```json
{"id": 1, "category": 1, "name": "Cola", "description": "", "selling_price": "2.50", "cost_price": "1.00",
 "quantity": 10, "minimum_stock": 3, "image": "", "created_at": "ISO", "updated_at": "ISO"}
```
- Required on create: `name`, `selling_price` (≥ 0). Optional: `category` (id or null), `description`, `cost_price` (nullable), `minimum_stock` (default 0), `image` (plain string ≤ 500 chars — there is **no image upload endpoint**).
- `quantity` is **read-only**. Set the opening stock with write-only `initial_quantity` (≥ 0) on **create**; afterwards change stock only via `adjust-stock` or sales.
- Never compute stock on the client; re-read the product.

| Method | Path | Notes |
|---|---|---|
| GET / POST | `/api/business/products/` | `?search=` (name), `?ordering=` — see [List query parameters](#list-query-parameters). No pagination |
| GET / PUT / PATCH / DELETE | `/api/business/products/{id}/` | DELETE of a product that has been sold → `400 {"detail": "This product has sales and cannot be deleted."}` |
| GET | `/api/business/products/low-stock/` | Products with `quantity <= minimum_stock` (includes out-of-stock) |
| GET | `/api/business/products/out-of-stock/` | Products with `quantity == 0` |
| POST | `/api/business/products/{id}/adjust-stock/` | see below |

### POST `/api/business/products/{id}/adjust-stock/`
Request:
```json
{"quantity": 5, "movement_type": "IN", "reason": "restock"}
```
- `quantity`: integer ≥ 0 (required). `movement_type`: `IN` (add), `OUT` (remove), `ADJUSTMENT` (**set** the quantity to this value). `reason` optional (≤ 255).
- `200` → the updated product object.
- Errors: `400` field errors (`{"quantity": [...]}`, `{"movement_type": [...]}`) for missing / negative / non-numeric quantity or unknown type; `400 {"detail": "Insufficient stock."}` (OUT more than available); unknown product / other user's product → `404 {"detail": "Product not found."}`.

---

## Customers

Fields: `id`, `name` (required), `phone`, `address`, `created_at`, `updated_at`.

| Method | Path | Notes |
|---|---|---|
| GET / POST | `/api/business/customers/` | `?search=` (name), `?ordering=` — see [List query parameters](#list-query-parameters). No pagination |
| GET / PUT / PATCH / DELETE | `/api/business/customers/{id}/` | Deleting a customer keeps their sales with `customer = null`; those sales no longer count in any customer's balance |
| GET | `/api/business/customers/{id}/history/` | Financial summary and sales of one customer (below) |

### GET `/api/business/customers/{id}/history/` — auth
```json
{
  "customer": {"id": 1, "name": "Omar", "phone": "0791", "address": "", "created_at": "ISO", "updated_at": "ISO"},
  "summary": {"total_purchases": "500.00", "total_paid": "350.00", "outstanding_balance": "150.00"},
  "sales": [ /* Sale objects, newest first (see Sales) */ ]
}
```
- `total_purchases` = sum of the customer's sale totals, `total_paid` = sum of what was paid on them (sale creation
  amount + recorded payments), `outstanding_balance = total_purchases − total_paid`. Calculated on every request,
  so edited or deleted sales and new payments are always reflected. A customer without sales gets `"0.00"` values and `"sales": []`.
- **Contract change:** this endpoint used to return only the array of sales. The array is now under `sales`.
- Unknown customer, or a customer of another business → `404 {"detail": "No Customer matches the given query."}`.

---

## Sales

Sale object:
```json
{"id": 1, "customer": 1, "total_amount": "10.00", "paid_amount": "5.00", "remaining_amount": "5.00",
 "payment_status": "PARTIAL", "sold_at": "ISO",
 "items": [{"id": 1, "product": 1, "quantity": 4, "unit_price": "2.50", "subtotal": "10.00"}]}
```
- `payment_status`: `PAID` | `PARTIAL` | `UNPAID`, computed by the server (BR-10). `customer` and `items[].product` are **IDs only** — the response has no customer or product names; look them up from the customer/product lists.
- **Historical prices:** `items[].unit_price` is the price at the time of the sale and never changes. Editing a product's
  `selling_price` affects only later sales. The client cannot send a price.
- Debts are represented by sales with `payment_status != PAID`. There is no separate debt entity and **no `?payment_status=` filter** (ignored) — filter on the client.

### POST `/api/business/sales/` — auth
```json
{"customer": 1, "paid_amount": "5.00", "items": [{"product": 1, "quantity": 4}]}
```
`items` required (≥ 1, each `quantity ≥ 1`); `customer` optional/null; `paid_amount` optional (default 0, ≥ 0). Stock is deducted by the server. If `paid_amount > 0` a CASH payment record is created.
`201` sale. Errors (400 `{"detail": ...}`): `"Insufficient stock for <name>."`, `"Invalid product."`, `"Invalid customer."`, `"Paid amount cannot exceed total amount."`; `{"items": ["At least one item is required."]}`.

### GET `/api/business/sales/` — auth
Array of sales, newest first. Query parameters: `date_from`, `date_to`, `ordering`, `page`, `page_size` — see
[List query parameters](#list-query-parameters). There is no `?payment_status=` filter.

### GET / PATCH / PUT / DELETE `/api/business/sales/{id}/` — auth
- PATCH/PUT body (all optional): `customer` (id or null) and `items` (`[{"product","quantity"}]`). PUT behaves like PATCH.
- **Payments cannot be edited here.** Sending `paid_amount`, `payment_status`, `remaining_amount` or `total_amount` returns
  `400 {"paid_amount": ["This field cannot be edited. Record payments with POST /api/business/sales/{id}/payments/."]}`
  and nothing is changed. Money received is recorded **only** through the payments endpoint below.
- Sending `items` sets the final list of items: stock of the previous items is restored and the new list is deducted.
  A product that was already on the sale **keeps its original `unit_price`** (only the quantity changes); a product added
  by the edit is priced at its current `selling_price`. Totals are recalculated.
- The new total may not be lower than what was already paid (`400 {"detail": "Paid amount cannot exceed total amount."}`, nothing is changed).
  `payment_status` and `remaining_amount` are recalculated on every edit.
- `DELETE` → `204`; stock is restored and its payments are deleted. Another user's sale → 404.

### POST `/api/business/sales/{sale_id}/payments/` — auth
The **only** way to record a payment after the sale was created (the optional `paid_amount` of `POST /sales/` records the first one).
```json
{"amount": "1.00", "payment_method": "CASH", "note": "optional"}
```
- `payment_method`: `CASH` | `CARD` | `OTHER`. Optional, defaults to `CASH`.
- `201`: `{"id": 2, "amount": "1.00", "payment_method": "CARD", "note": "x", "payment_date": "ISO"}`. The sale's `paid_amount`, `remaining_amount` and `payment_status` are updated; re-fetch the sale.
- Errors (400 `{"detail": ...}`): `"Payment must be greater than zero."`, `"Payment cannot exceed remaining amount."`, `"Sale not found."` (also for another user's sale); invalid method → `{"payment_method": ["\"BTC\" is not a valid choice."]}`.
- ⚠️ There is **no** `GET` for payments and sales do not embed them, so payment history cannot be displayed.

---

## Expenses

Fields: `id`, `amount` (required), `category` (required free-text string ≤ 100, e.g. `"rent"`), `description`, `expense_date` (required `YYYY-MM-DD`), `created_at`.

| Method | Path | Notes |
|---|---|---|
| GET / POST | `/api/business/expenses/` | `?category=<exact text>`, `date_from`, `date_to`, `ordering`, `page`, `page_size` — see [List query parameters](#list-query-parameters) |
| GET / PUT / PATCH / DELETE | `/api/business/expenses/{id}/` | |

Missing `expense_date` → `400 {"expense_date": ["This field is required."]}`. Categories are plain text, not a managed list.

---

## Invoices

Sprint 3 (FR-19, FR-20, BR-11, BR-12, UC-5). An invoice is a **frozen snapshot** of a sale at the moment
it is issued: once created, its stored fields never change, even if the underlying sale, its items, its
customer, or a product are edited or deleted afterwards. There is no way to create an invoice except from
an existing sale, and there is no generic update endpoint — only cancellation.

Invoice object:
```json
{
  "id": 1,
  "sale": 1,
  "invoice_number": "INV-20260924-0001",
  "status": "ISSUED",
  "issued_at": "2026-09-24T12:01:30.627966Z",
  "customer_name": "",
  "customer_phone": "",
  "total": "20.00",
  "notes": "",
  "items": [
    {"id": 1, "product_name": "Cola", "quantity": 2, "unit_price": "10.00", "line_total": "20.00"}
  ]
}
```
- `invoice_number` format `INV-YYYYMMDD-0001`, unique **per business per day**; allocated under a database
  row lock so two simultaneous requests can never receive the same number.
- `status`: `ISSUED` | `CANCELLED`.
- `customer_name`/`customer_phone` and every row in `items[]` are a **copy** taken at issue time from the
  sale's customer and sale items. They are never looked up live again, so a later rename, price change, or
  even deleting the customer/product afterwards has no effect on an already-issued invoice. If the sale had
  no customer, both fields are `""` (no data is invented).
- `total` is a copy of the sale's `total_amount` at issue time.
- At most one **active** (`ISSUED`) invoice can exist per sale at a time — but a sale whose only invoice was
  cancelled can be invoiced again (BR-12's "cancel and reissue"); the cancelled invoice is kept, unchanged,
  alongside the new one.

| Method | Path | Notes |
|---|---|---|
| POST | `/api/business/sales/{sale_id}/invoice/` | Create an invoice from this sale |
| GET | `/api/business/invoices/` | List, newest first — see [List query parameters](#list-query-parameters) |
| GET | `/api/business/invoices/{id}/` | Detail, including `items` |
| POST | `/api/business/invoices/{id}/cancel/` | `ISSUED` → `CANCELLED` |
| GET | `/api/business/invoices/{id}/pdf/` | `200`, `Content-Type: application/pdf` |

### POST `/api/business/sales/{sale_id}/invoice/` — auth
Request body: `{"notes": "optional, ≤ 500 chars"}` (or `{}`).
- `sale_id` must belong to the caller's business → unknown or another business's sale → `404`.
- BR-11: a second attempt while the sale already has an active invoice →
  `400 {"detail": "An invoice already exists for this sale."}`.
- `201` → the invoice object above.
- There is **no** `POST /api/business/invoices/` that takes a manually supplied sale/customer/items —
  invoices can only be created through this sale-scoped endpoint.

### POST `/api/business/invoices/{id}/cancel/` — auth
- `ISSUED` → `CANCELLED`. `200` → the invoice object (`"status": "CANCELLED"`).
- Cancelling an already-cancelled invoice → `400 {"detail": "Invoice is already cancelled."}`.
- Cancellation changes only the invoice's own `status`. It never deletes the invoice or its items, never
  touches the linked sale or its payments, and never restores stock.
- Unknown invoice, or one belonging to another business → `404`.

### GET `/api/business/invoices/{id}/pdf/` — auth
- `200`, `Content-Type: application/pdf`; the body is the raw PDF (business name/contact info, invoice
  number, issue date, status, customer name/phone, the item table, total, notes), rendered **only** from the
  stored Invoice/InvoiceItem snapshot — never from the live sale/product/customer records.
- A cancelled invoice's PDF is still available and shows `"status": "CANCELLED"`.
- Unknown invoice, or one belonging to another business → `404`.

### Deleting a sale that has an invoice
`DELETE /api/business/sales/{id}/` on a sale that has any invoice (issued or cancelled) is rejected:
`400 {"detail": "This sale has an invoice and cannot be deleted."}`. The sale and its invoice(s) are
unaffected.

---

## Debts

Sprint 3 (FR-13, FR-15, BR-8, BR-9, BR-10, UC-4). This is a **separate, standalone** entity mainly for debts
the business owes to others (`PAYABLE`, e.g. suppliers) — it does not replace or duplicate the existing
receivable tracking already provided by `Sale`/`Payment` (an unpaid or partially-paid sale). A `RECEIVABLE`
debt type also exists (see [Reports](#reports) for why it is not double-counted with `Sale`-based
receivables in the performance report).

Debt object:
```json
{
  "id": 1,
  "debt_type": "PAYABLE",
  "party_name": "Supplier A",
  "customer": null,
  "sale": null,
  "original_amount": "500.00",
  "paid_amount": "500.00",
  "remaining_amount": "0.00",
  "due_date": "2026-10-01",
  "status": "PAID",
  "notes": "October stock",
  "created_at": "2026-09-24T12:01:30.822752Z",
  "updated_at": "2026-09-24T12:01:30.856804Z"
}
```
- `debt_type`: `RECEIVABLE` | `PAYABLE` — mandatory on create (BR-8), never optional/defaulted.
- `status`: `UNPAID` | `PARTIAL` | `PAID`, computed by the server from `paid_amount` vs. `original_amount`
  (BR-10) — never accepted from the client.
- `remaining_amount = original_amount - paid_amount` (read-only, like `Sale.remaining_amount`).
- `customer`/`sale` are optional foreign keys (ids), for linking a `RECEIVABLE` debt back to where it came
  from; both are usually `null` for a `PAYABLE` debt.
- There is **no `DELETE`** for debts (`405`): BR-9 ("a debt with transaction history must not be silently
  deleted") is satisfied by never exposing deletion at all, rather than adding a confirmation flow.

| Method | Path | Notes |
|---|---|---|
| GET / POST | `/api/business/debts/` | `?type=`, `?status=`, `?due_before=`, `?search=` (`party_name`), `?ordering=` — see [List query parameters](#list-query-parameters) |
| GET / PATCH / PUT | `/api/business/debts/{id}/` | `PUT` behaves like `PATCH` (same convention as Sale); `DELETE` not supported (405) |
| POST | `/api/business/debts/{id}/payments/` | Record a payment (see below) |
| GET | `/api/business/debts/due/` | Debts due soon (see below) |

### POST `/api/business/debts/` — auth
```json
{"debt_type": "PAYABLE", "party_name": "Supplier A", "original_amount": "500.00",
 "due_date": "2026-10-01", "notes": "October stock"}
```
`debt_type`, `party_name`, `original_amount` (≥ 0) required; `customer`, `sale` (ids, scoped to the caller's
business — a foreign or unknown id → `400`), `due_date`, `notes` (≤ 500 chars) optional. `201` → the debt
object, `paid_amount: "0.00"`, `status: "UNPAID"`.
Errors (400): `{"debt_type": ["This field is required."]}` / `["\"X\" is not a valid choice."]`,
`{"original_amount": ["Ensure this value is greater than or equal to 0."]}`; an unknown `customer`/`sale`
id, **or one belonging to another business**, → `{"detail": "Invalid customer."}` / `{"detail": "Invalid sale."}`
(not a field error — these are checked in the service layer, after the serializer's own field validation
already passed).

### GET `/api/business/debts/` and GET `/api/business/debts/{id}/` — auth
List, or one debt scoped to the caller's business; unknown/foreign id → `404`.
`?due_before=YYYY-MM-DD` filters to debts due on or before that date; a malformed value →
`400 {"due_before": "Date has wrong format. Use YYYY-MM-DD."}` (plain string, not a list). `?type=` and
`?status=` filter on exact `debt_type`/`status` values; an unrecognised value simply matches nothing
(no error), the same leniency as an unknown `?ordering=` field elsewhere in this API.

### PATCH / PUT `/api/business/debts/{id}/` — auth
Only `party_name`, `due_date`, `notes` are editable. `paid_amount`, `status`, `debt_type`,
`original_amount`, `customer`, `sale`, `business` are rejected — same convention as `Sale`'s update
endpoint:
```json
{"paid_amount": ["This field cannot be edited. Record payments with POST /api/business/debts/{id}/payments/."]}
```
A rejected request changes nothing, even the fields that would otherwise have been valid. `PUT` behaves
exactly like `PATCH` here (all fields are optional either way — again, the same convention `Sale` already
uses). `DELETE` is not supported (405). Unknown/foreign debt → `404`.

### POST `/api/business/debts/{id}/payments/` — auth
The only way to change `paid_amount`.
```json
{"amount": "100.00", "note": "optional, ≤ 255 chars"}
```
- `amount` must be `> 0` and `<= remaining_amount`; `amount ≤ 0` → a field error
  (`{"amount": ["Ensure this value is greater than or equal to 0.01."]}`); exceeding the remaining balance →
  `400 {"detail": "Payment cannot exceed remaining amount."}`.
- `201` → `{"id": 1, "debt": 1, "amount": "100.00", "note": "", "created_at": "ISO"}`. The debt's
  `paid_amount`/`remaining_amount`/`status` are updated; re-fetch the debt to see them.
- Multiple partial payments are supported; the debt becomes `PAID` only once `paid_amount` exactly equals
  `original_amount` (BR-10).
- Unknown/foreign debt → `404`.

### GET `/api/business/debts/due/` — auth
```
GET /api/business/debts/due/?days=7
```
Returns debts whose `due_date` is from **today through today + `days`** (inclusive), excluding `PAID`
debts and debts with no `due_date`. `days` defaults to `7` if omitted; must be a non-negative integer,
otherwise `400 {"days": "Must be an integer."}` or `400 {"days": "Must not be negative."}` (plain string,
not a list — this one is a manual check, not a serializer field).
**Note:** this is literally "today through today + N days" — an **overdue** debt (`due_date` in the past)
is *not* included. Response is a plain array of debt objects (no pagination).

### Notifications (FR-15)
FR-15 asks for an alert when a debt is due or about to become due. This sprint implements only the data
endpoint above (`GET .../debts/due/`) for the Android app to poll and show its own in-app alert/badge.
**No push notification (FCM) infrastructure exists or is planned for this sprint** — there was no existing
notification system to build on, and it is explicitly out of scope.

---

## Reports

Sprint 3 (FR-11, FR-24, FR-25, UC-3). Both endpoints use the server time zone (`TIME_ZONE = UTC`), the same
as the plain `dashboard/` endpoint — "today" is a UTC calendar day, not the merchant's local time.

### GET `/api/business/dashboard/series/` — auth
Time series for charting (FR-11, FR-25): one point per day/week/month, each with `sales`, `expenses` and
`profit = sales - expenses` for that bucket.
```
GET /api/business/dashboard/series/?period=day&from=2026-09-20&to=2026-09-22
```
```json
{
  "series": [
    {"period": "2026-09-20", "sales": "10.00", "expenses": "2.00", "profit": "8.00"},
    {"period": "2026-09-21", "sales": "5.00", "expenses": "0.00", "profit": "5.00"},
    {"period": "2026-09-22", "sales": "0.00", "expenses": "0.00", "profit": "0.00"}
  ]
}
```
- `period`: `day` (default) | `week` | `month`. Invalid value → `400 {"period": ["\"X\" is not a valid choice."]}`.
- `from`/`to` (`YYYY-MM-DD`, inclusive). **Default when omitted:** a trailing window of 7 points ending at
  `to` (default `to`: today) — e.g. `period=day` with nothing supplied returns the last 7 days including
  today. Malformed date → the same shape as `date_from`/`date_to` elsewhere in this API:
  `400 {"from": ["Date has wrong format. Use one of these formats instead: YYYY-MM-DD."]}` (or `{"to": [...]}`).
  `from` after `to` → `400 {"to": "to must not be earlier than from."}` (a plain string here, not a list —
  this check, unlike the date-format one, isn't a serializer field error).
- `period` label is the **start date** of that bucket. A `week` point is always a full **Monday–Sunday**
  week and a `month` point a full **calendar month** — the same definitions the plain `dashboard/` endpoint
  already uses for its own `week`/`month` figures — even if that extends slightly outside the requested
  `from`/`to` at the edges.
- A request that would produce more than 366 points is rejected (`400 {"to": "Range is too large..."}`) —
  a safety limit, not a documented business rule.

### GET `/api/business/reports/performance/` — auth
A comprehensive snapshot (FR-24): sales/expenses/profit for a period, plus the business's **current**
outstanding balances and stock alerts.
```
GET /api/business/reports/performance/?from=2026-09-01&to=2026-09-30
```
```json
{
  "total_sales": "100.00",
  "total_expenses": "40.00",
  "profit": "60.00",
  "outstanding_receivables": "30.00",
  "outstanding_payables": "130.00",
  "low_stock_count": 2
}
```
- `total_sales`, `total_expenses`, `profit` are scoped to `from`/`to` (inclusive `YYYY-MM-DD`).
  **Default when both are omitted:** the whole current calendar month (matching `dashboard/`'s own
  `month` figure, which spans the full month even for days that haven't happened yet). Supplying only one
  of `from`/`to` falls back to today / the 1st of that month for the other side instead of the whole-month
  default. Invalid date / `from` after `to` → same 400 shapes as the series endpoint above.
- `outstanding_receivables` and `outstanding_payables` are **not** scoped to `from`/`to` — they are the
  business's live balances right now, the same way `GET /customers/{id}/history/` already reports a live
  `outstanding_balance` regardless of any date filter.
- **How receivables/payables avoid double-counting:** `outstanding_receivables` is calculated only from
  `Sale`/`Payment` (`total_amount - paid_amount` summed over every sale) — the pre-existing source of truth
  for money owed *to* the business. `outstanding_payables` is calculated only from `Debt` where
  `debt_type = "PAYABLE"` (`original_amount - paid_amount`). A `RECEIVABLE` debt is **never** added to
  either figure, so a receivable is never counted twice.
- `low_stock_count`: number of products with `quantity <= minimum_stock` — the exact same rule as
  `GET /products/low-stock/`.

---

## Not available (do not build against these)

Real push notifications / alerts (FCM or similar), backup / restore, phone/email verification (OTP),
product image upload, a `?payment_status=` filter on sales, a `GET` list of a sale's payments (payments
still cannot be listed — only recorded via `POST .../payments/`), and `DELETE` on a debt.

## Integration checklist (verified against the running API)

| # | Check | Result |
|---|---|---|
| 1 | Register / login / me / refresh / refresh-reuse / change-password / reset-request | ✅ as documented |
| 2 | Password-reset confirm | ⚪ by code only (needs the emailed token) |
| 3 | Logout | ⚪ by code + missing-refresh case verified |
| 4 | Business create / get / patch / duplicate | ✅ |
| 5 | Products create / list / adjust (IN, OUT, bad type, 404) / low & out-of-stock | ✅ |
| 6 | Product delete after sale · negative adjust | ✅ 400 with a message (was 500) |
| 7 | Sales create + all validation errors, list, detail, delete | ✅ |
| 8 | Payments (valid, zero, negative, over-remaining, bad method, missing method) | ✅ |
| 9 | Sale PATCH: `paid_amount` rejected, paid ≤ total enforced, status recomputed, historical prices kept | ✅ |
| 10 | Customers create / search / order / history + balance summary | ✅ |
| 11 | Expenses create / list / `?category` / date filters / validation | ✅ |
| 11b | Sales and expenses: date filters, ordering, opt-in pagination | ✅ |
| 12 | Dashboard today / week / month | ✅ decimal strings |
| 13 | User A cannot read/change user B's product, sale, customer, expense, payment, stock; B's lists/dashboard are empty | ✅ |
| 14 | Unauthenticated requests → 401 | ✅ |
| 15 | Invoices: create / duplicate rejected / snapshot survives product & customer edits / cancel / re-cancel rejected / cancelled stays readable / reissue after cancel / PDF 200 + `application/pdf` / sale-with-invoice delete rejected / cross-user 404 | ✅ (Sprint 3) |
| 16 | Debts: create (payable & receivable) / invalid type / negative amount / `PATCH` protects money fields / payments (zero, negative, over-remaining, partial×N, exact final → `PAID`) / `due/` window & `PAID` exclusion / filters (`type`, `status`, `due_before`, `search`) / cross-user 404 | ✅ (Sprint 3) |
| 17 | Reports: `dashboard/series/` bucketing (day/week/month), defaults, invalid `period`, range-too-large; `reports/performance/` aggregation, current-month default, receivables/payables not double-counted, low-stock count, cross-user isolation | ✅ (Sprint 3) |
| 18 | Profile: `PATCH /api/auth/me/` allowed fields, protected fields (400, nothing applied), unauthenticated 401, `GET` shape unchanged | ✅ (Sprint 3) |

Checks 15–18 are backed by the automated test suite (`business/tests/test_invoices.py`,
`test_debts.py`, `test_reports.py`, `accounts/tests/test_profile.py`) rather than manual `curl` calls, the
same as the rest of this checklist's underlying verification since Sprint 2.
