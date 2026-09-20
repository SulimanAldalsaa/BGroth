# BGroth — API Gap Report

Scope: backend on `origin/main` (commit `5d437f8`) checked against the SRS v1.1 (FR-1..28, NFR-1..14,
BR-1..14, UC-1..6, AC-1..9). **The Android project was not available**, so no Android code was
inspected; "Android" columns are marked *not assessed*. The Figma screens were not opened; only the
screen names in the overview image were used, so UI ↔ API mismatches below are inferred from those names.

How it was checked: source review of every file in `accounts/` and `business/`, ~90 live requests
through Django's test client on a throw-away in-memory SQLite database, and OpenAPI schema generation.
On `origin/main` there were **0 tests** (all `business/tests/*.py` were empty). This branch adds **33 tests**
(auth flow, business, categories, products/stock, customers, sales, payments, expenses, dashboard and
cross-user isolation) that pass on PostgreSQL.

**Fixed in this branch:** #1, #2, #3, #4, #6, #10 (decimal strings), #15 (Swagger schemas) and
cross-user PATCH/DELETE of a sale now returns 404. Everything else below is still open.

Legend: ✅ works · ⚠️ works with a problem · ❌ missing / broken · ⚪ not assessed.

## A. Android features already implemented
⚪ Not assessed — no Android project was provided.

## B. Android features missing
⚪ Not assessed.

## C. Backend APIs already available
Auth (register, login, logout, refresh, me, change-password, password-reset request/confirm) ·
Business (get/create/patch) · Dashboard (today only) · Categories CRUD · Products CRUD + low-stock,
out-of-stock, adjust-stock · Customers CRUD + history · Sales CRUD · Payments (create) · Expenses CRUD.
25 routes; all appear in `/api/schema/`. Details in [`API.md`](API.md).

## D. Backend APIs missing
Invoices / PDF (FR-19, 20) · notifications / alerts (FR-15, 18) · backup / restore (FR-26, 27) ·
weekly / monthly profit and chart series (FR-10, 11, 25) · full report (FR-24) · debts owed to
suppliers (FR-13, BR-8) · debt due date (FR-15) · user-profile update (FR-2) · payments list ·
customer balance totals · phone/email verification (OTP screen exists in the design) ·
date filters on sales/expenses (FR-4, 8) · search · pagination.

## E. API mismatches / bugs (reproduced)

| # | Endpoint | Problem | Reproduction (verified) | Impact |
|---|---|---|---|---|
| 1 ✅ | `POST /sales/{id}/payments/` | **500** when `payment_method` is omitted. The serializer treats it as optional (model default) but `payment_method=serializer.validated_data["payment_method"]` raises `KeyError` (`business/views/payment.py`) | `{"amount":"1"}` → 500 HTML | Android must always send it until fixed |
| 2 ✅ | `POST /products/{id}/adjust-stock/` | **500** on negative `quantity` (`CHECK constraint failed: quantity`) | `{"quantity":-5,"movement_type":"ADJUSTMENT"}` | crash on bad input |
| 3 ✅ | same | Non-numeric quantity returns a raw Python message in `detail` | `{"quantity":"abc"}` → `invalid literal for int()…` | leaks internals |
| 4 ✅ | `DELETE /products/{id}/` | **500** if the product was ever sold (`SaleItem.product` is `PROTECT`, `ProtectedError` uncaught) | sell 1 unit, delete product | cannot delete products with history |
| 5 | `PATCH /sales/{id}/` `paid_amount` | Changes `paid_amount` **without creating a `Payment` row** | paid 6.00 in payments, PATCH 10.00 → `paid_amount 10.00`, payments sum 6.00 | inconsistent money history |
| 6 ✅ | `PATCH /sales/{id}/` `items` | New total can be below `paid_amount`; not re-validated | items→1 unit: `total 2.50, paid 10.00, remaining -7.50, PAID` | negative debt; violates BR-10 |
| 7 | `PATCH /sales/{id}/` `items` | Re-prices **all** items at the product's current price, losing historical `unit_price` | code (`sale_service.update_sale`) | history changes when prices change |
| 8 | Login | Wrong credentials → **400**, not 401 | `POST /login/` bad password | client must not treat login 400 as "session expired" |
| 9 | Logout | Error body uses `{"error": ...}` instead of `{"detail": ...}` | missing refresh | inconsistent error handling |
| 10 ⚠️ | Dashboard | Only *today*; (decimal strings now consistent); "today" is UTC not local | see API.md | wrong day boundary for Jordan (UTC+3) |
| 11 | Lists | Filters silently ignored: `?search=`, `?date=`, `?payment_status=`, `?expense_date=` all returned unfiltered data | live calls | Android would show wrong data if it assumes filtering |
| 12 | Lists | No `ordering` on any queryset and no pagination | code | unstable order, large payloads |
| 13 | `GET /customers/{id}/history/` | Unknown / foreign id returns `200 []` instead of 404 | live | hides errors |
| 14 | Sale responses | `customer` and `items[].product` are IDs only (no names) | live | History/Sales screens need N extra lookups |
| 15 ✅ | Swagger (fixed: serializers/`extend_schema` added) | `BusinessView`, `DashboardView`, `ProductStockAdjustView`, `PaymentCreateView` have **no schema** (spectacular: "unable to guess serializer") | schema generation | Kotlin team can't generate models for them; use `API.md` |
| 16 | Password reset | `send_mail(..., fail_silently=False)` runs only when the account exists → with broken SMTP an existing email gives **500** and an unknown one gives 200 | code | user enumeration + failure (not run: needs SMTP) |
| 17 | Sales with no customer | An `UNPAID`/`PARTIAL` sale may have `customer = null` | code | a debt with no debtor |
| 18 | Deleting a sale | Deletes its payments with no confirmation | live (204) | BR-9 not enforced |

## F. UI / API mismatches (inferred from screen names)
| Screen(s) in design | Backend reality |
|---|---|
| Create account ×3 / Verify | No phone field, no OTP/verification endpoint (`is_email_verified` is never set) |
| Personal Profile | No user-update endpoint |
| Business Setup | ✅ `POST /api/business/` (fields: name, description, phone, address, city, country) |
| Dashboard | Only today's sales/expenses/profit |
| Add Product / Category / Products / Stock / Adjust Quantity | ✅ endpoints exist; product `image` is a plain string, no upload |
| Sales / History Sales / Edit Sale | ✅ create/list/edit/delete; no date filter; edit has bugs #5–#7 |
| Recent sales, customer history | ✅ data exists, without names (bug #14) |

## G. SRS coverage (backend view; Android not assessed)

| Req | Status | Note |
|---|---|---|
| FR-1 account + login | ✅ | JWT, refresh rotation |
| FR-2 edit account & business data | ⚠️ | business PATCH ✅; user profile ❌ |
| FR-3 record sale | ✅ | client cannot enter a manual price (UC-1 step 3 says "or the user enters it manually") |
| FR-4 sales record + date filter | ⚠️ | list ✅, date filter ❌ |
| FR-5 edit / delete sale | ⚠️ | works, with bugs #5–#7 |
| FR-6 record expense | ✅ | |
| FR-7 categorise expenses | ⚠️ | free-text `category`, no managed types |
| FR-8 expense history filter date/type | ⚠️ | type ✅ (exact match), date ❌ |
| FR-9 automatic profit | ⚠️ | today only |
| FR-10 daily/weekly/monthly profit | ❌ | |
| FR-11 profit graph | ❌ | no time-series endpoint |
| FR-12 debts owed by customers | ⚠️ | = unpaid/partial sales; no filter, no per-customer balance |
| FR-13 debts owed to suppliers | ❌ | |
| FR-14 debt status paid/partial/unpaid | ✅ | via payments (server computes status) |
| FR-15 due-date alerts | ❌ | no due date, no notifications |
| FR-16 add products with quantity | ✅ | `initial_quantity` |
| FR-17 auto stock update on sale | ✅ | stock deduction observed to reject over-sale; restored on delete |
| FR-18 low-stock alert | ⚠️ | `products/low-stock/` list only; no push |
| FR-19, FR-20 invoice + PDF | ❌ | **MISSING BACKEND** |
| FR-21 add customer | ✅ | name + phone |
| FR-22 link sales/balances to customer | ⚠️ | `sale.customer` ✅; balance ❌ |
| FR-23 customer history | ⚠️ | sales list only, no totals |
| FR-24, FR-25 reports & graphs | ❌ | **MISSING BACKEND** |
| FR-26, FR-27 backup / restore | ❌ | **MISSING BACKEND** |
| FR-28 Arabic / English | ⚪ | client feature; note all server messages are English only |
| NFR-3 encryption in transit / at rest | ⚠️ | no HTTPS settings in the project; not verifiable here |
| NFR-4 / BR-1 / AC-7 data isolation | ✅ | 11 cross-user attempts → 404 / empty (see below) |
| NFR-5 secure login | ✅ | PBKDF2 hashes, generic login error; no login throttle |
| BR-2 one business per user | ✅ | |
| BR-3, BR-4, BR-5 stock rules | ✅ | |
| BR-6 / BR-7 profit rule | ⚠️ | formula ✅ (Sales − Expenses), read-only ✅, periods ❌ |
| BR-8 debt type | ❌ | only receivables |
| BR-9 confirm before deleting debt with history | ❌ | not enforced (#18) |
| BR-10 paid only when total matches | ⚠️ | ✅ via payments; broken by #5/#6 |
| BR-11, BR-12 invoices | ❌ | |
| BR-13, BR-14 backup | ❌ | |
| UC-1 / AC-1 record sale | ✅ | |
| UC-2 / AC-2 expense | ✅ | |
| UC-3 / AC-3 profit | ⚠️ | |
| UC-4 / AC-4 debts | ⚠️ | |
| UC-5 / AC-5 invoice | ❌ | |
| UC-6 / AC-6 low-stock alert | ⚠️ | list only |
| AC-8 backup/restore · AC-9 bilingual | ❌ · ⚪ | |

## Cross-user isolation test (User A vs User B)
All returned no data or 404: list products, GET product, sale, customer, expense; DELETE
expense; adjust stock; pay sale (`400 "Sale not found."`); sell A's product (`"Invalid product."`);
A-customer history (`[]`); B's dashboard (zeros). Unauthenticated → 401. **Not covered:** the same
attempts through PATCH/PUT on every resource, and PostgreSQL-specific behaviour.

## H. Security findings

| Severity | Finding | Action |
|---|---|---|
| **High** | The PostgreSQL password was hard-coded in `authproject/settings.py` and is present in **every commit** on `origin/main` (≥ 6 commits, public GitHub remote). | **Rotate the database password now.** Removing it from the latest file (done in this branch) does not remove it from history; optionally rewrite history (`git filter-repo`) after rotating. |
| **High** | `data.json` (UTF-16 fixture, committed) contains 4 real-looking user accounts (emails + PBKDF2 password hashes, **2 superusers**), a session record and admin log entries. | Delete it from the repo/history; reset those passwords; invalidate sessions. |
| Medium | A teammate's personal email address is the hard-coded default of `DEFAULT_FROM_EMAIL`. | Move to env only (`.env.example` now has a placeholder). |
| Medium | `DEBUG = True`, `ALLOWED_HOSTS = ["*"]`, `CORS_ALLOW_ALL_ORIGINS = True`, and a known fallback `SECRET_KEY` if the env var is missing. 500 errors render Django debug pages. | Drive all four from env; fail to start in production without a secret key. |
| Medium | No HTTPS/HSTS/secure-cookie settings; `CSRF_TRUSTED_ORIGINS` allows `https://*.trycloudflare.com` (dev tunnel). SRS requires HTTPS. | Terminate TLS in front of Django and set `SECURE_*` flags for production. |
| Medium | No throttling on login/register (only password-reset request). | Add DRF throttles. |
| Low | Unpinned `requirements.txt` (`>=`). | Pin versions. |
| Low | Raw exception text returned in one 400 (#3); password change does not revoke existing tokens. | Fix / blacklist on change. |
| ✅ | Secrets in this branch: DB credentials now from `DB_*` env vars; `.env` is git-ignored; `.env.example` holds placeholders only. | |

Nothing from the backend secrets was copied into the Android side or into these documents.

## I. Documentation issues
- The old `README.md` described an auth-only project → rewritten. `README_en.md` was an identical
  copy of it (removed in this branch to avoid two stale copies).
- Swagger title/description said "Auth API" → now "BGroth API"; four views still lack schemas (#15).
- No LICENSE in the repo (see below).

## J. Recommended next actions (in order)
1. Rotate the DB password; remove `data.json` and reset those accounts.
2. Fix bug #5 (`paid_amount` PATCH without a payment row) and #7 (re-pricing on edit).
3. Add: payments list (or embed `payments` in the sale), customer/product names in sale responses,
   `?date_from`/`?date_to`/`?payment_status`/`?customer` filters, ordering + pagination.
4. Extend the dashboard: week/month periods, chart series, outstanding debts, low-stock count.
5. Decide and build the missing modules in SRS order of value: debts (due date, supplier debts),
   invoices/PDF, notifications (FCM), backup/restore, `PATCH /me/`.
6. Extend the test suite as new modules are added.
7. Ask the Android team to confirm OTP/verification scope with the design.

## LICENSE
No license file exists and project ownership is not defined (university project with six named
contributors). **Not created**, per the team decision to defer. Options when the team decides: MIT
(open), or an "All rights reserved" notice.
