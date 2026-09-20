# BGroth API Reference (for the Android / Kotlin team)

Derived from the backend source and **verified by calling the running API** and by the automated test suite
(`python manage.py test`, 33 tests). Where behaviour is a bug or a gap it is flagged
with ⚠️ — see [`GAP_REPORT.md`](GAP_REPORT.md) for the full list.

Base URL: see the README (`http://10.0.2.2:8000/` from the emulator). All bodies are JSON
(`Content-Type: application/json`).

## Conventions

| Topic | Behaviour |
|---|---|
| Auth header | `Authorization: Bearer <access_token>` on everything except register, login, token refresh, password-reset |
| IDs | integers, except `User.id` which is a UUID string |
| Money / decimals | JSON **strings** with 2 decimals, e.g. `"2.50"` (including the dashboard). Send them as strings or numbers |
| Dates | `datetime` = ISO-8601 UTC (`2026-09-20T15:03:13.042807Z`); `expense_date` = `YYYY-MM-DD` |
| Lists | Plain JSON array. **No pagination, no filtering (except `?category=` on expenses), no guaranteed order** |
| Business required | Every `/api/business/*` endpoint except `POST /api/business/` returns `404 {"detail": "Business not found. Please create a business first."}` until the user creates a business |

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
`200` user object (same as `user` above). ⚠️ No `PATCH`/`PUT` (405): the user's name cannot be edited.

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
{"sales_today": "2.50", "expenses_today": "0.00", "profit_today": "2.50"}
```
- Only **today**, only these three numbers. No week/month, no chart series, no debts, no inventory/low-stock counts.
- `profit_today = sales_today − expenses_today` (total of sale amounts, paid or not).
- ⚠️ "Today" is computed in server time (`TIME_ZONE = UTC`), not the merchant's time zone.

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
| GET / POST | `/api/business/products/` | No search/filter/pagination (`?search=` is ignored) |
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
| GET / POST | `/api/business/customers/` | no search |
| GET / PUT / PATCH / DELETE | `/api/business/customers/{id}/` | Deleting a customer keeps their sales with `customer = null` (their balance becomes ownerless) |
| GET | `/api/business/customers/{id}/history/` | Array of **sales** (same shape as Sale, below). No totals; an unknown id returns `200 []` |

Outstanding balance per customer is **not** provided; sum `remaining_amount` of the history on the client
only as a display aid until the backend adds it.

---

## Sales

Sale object:
```json
{"id": 1, "customer": 1, "total_amount": "10.00", "paid_amount": "5.00", "remaining_amount": "5.00",
 "payment_status": "PARTIAL", "sold_at": "ISO",
 "items": [{"id": 1, "product": 1, "quantity": 4, "unit_price": "2.50", "subtotal": "10.00"}]}
```
- `payment_status`: `PAID` | `PARTIAL` | `UNPAID`, computed by the server (BR-10). `customer` and `items[].product` are **IDs only** — the response has no customer or product names; look them up from the customer/product lists.
- Prices come from the product's current `selling_price`; the client cannot send a price.
- Debts are represented by sales with `payment_status != PAID`. There is no separate debt entity and **no `?payment_status=` filter** (ignored) — filter on the client.

### POST `/api/business/sales/` — auth
```json
{"customer": 1, "paid_amount": "5.00", "items": [{"product": 1, "quantity": 4}]}
```
`items` required (≥ 1, each `quantity ≥ 1`); `customer` optional/null; `paid_amount` optional (default 0, ≥ 0). Stock is deducted by the server. If `paid_amount > 0` a CASH payment record is created.
`201` sale. Errors (400 `{"detail": ...}`): `"Insufficient stock for <name>."`, `"Invalid product."`, `"Invalid customer."`, `"Paid amount cannot exceed total amount."`; `{"items": ["At least one item is required."]}`.

### GET `/api/business/sales/` — auth
Array of sales. ⚠️ No date filter (`?date=` ignored), no ordering guarantee, no pagination.

### GET / PATCH / PUT / DELETE `/api/business/sales/{id}/` — auth
- PATCH/PUT body (all optional): `customer` (id or null), `paid_amount`, `items` (`[{"product","quantity"}]`). PUT behaves like PATCH.
- Sending `items` **replaces all items**: old stock is restored, new items are priced at the product's *current* price.
- The resulting `paid_amount` may not exceed the new total (`400 {"detail": "Paid amount cannot exceed total amount."}`, nothing is changed). `payment_status` is recomputed on every edit.
- `DELETE` → `204`; stock is restored and its payments are deleted. Another user's sale → 404.
- ⚠️ Setting `paid_amount` through PATCH does **not** create a payment record. Use the payments endpoint for money received so history stays accurate.

### POST `/api/business/sales/{sale_id}/payments/` — auth
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
| GET / POST | `/api/business/expenses/` | Only filter: `?category=<exact text>`. ⚠️ No date filter, no ordering |
| GET / PUT / PATCH / DELETE | `/api/business/expenses/{id}/` | |

Missing `expense_date` → `400 {"expense_date": ["This field is required."]}`. Categories are plain text, not a managed list.

---

## Not available (do not build against these)

Invoices / PDF, notifications / alerts, backup / restore, reports & chart series (weekly/monthly),
debts owed to suppliers, debt due dates, `PATCH /api/auth/me/`, phone/email verification (OTP), file upload,
search, pagination, date filters.

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
| 9 | Sale PATCH (paid ≤ total enforced, status recomputed) | ✅ · ⚠️ `paid_amount` edit creates no payment row |
| 10 | Customers create / history | ✅ |
| 11 | Expenses create / list / `?category` / validation | ✅ |
| 12 | Dashboard | ✅ decimal strings · ⚠️ today only |
| 13 | User A cannot read/change user B's product, sale, customer, expense, payment, stock; B's lists/dashboard are empty | ✅ |
| 14 | Unauthenticated requests → 401 | ✅ |
