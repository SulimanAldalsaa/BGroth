# BGroth Backend

REST API for **BGroth**, a small-business management app for merchants (sales, expenses, inventory,
customers, payments/debts and a daily dashboard). The API is consumed by the native Android app
(Kotlin + Jetpack Compose).

> Status: MVP backend, Sprint 3 complete. Authentication (incl. profile update), business profile,
> categories, products/inventory, customers, sales, payments, expenses, invoices (+ PDF), debts
> (payable/receivable) and performance reports/chart series are implemented. Real push notifications and
> backup/restore are **not** implemented — see [Known limitations](#known-limitations--missing-features)
> and [`docs/GAP_REPORT.md`](docs/GAP_REPORT.md) (pre-Sprint-3; invoices/debts/reports/profile it lists as
> missing are now done).

## Project overview

There is a single user type (the merchant). Each user owns exactly one business and can only see
their own data. There is no admin role in the mobile app (Django admin exists for developers only).

## Architecture

```
Android app  ──HTTPS/JSON + JWT──▶  Django REST Framework  ──▶  PostgreSQL
                                    views → services / selectors → models
```

- **views** – HTTP layer, permission checks, status codes.
- **serializers** – validation and JSON shape.
- **services** – write operations that change state (sales, payments, stock) inside DB transactions.
- **selectors** – read-only queries (dashboard, product lists).

## Technology stack

- Python, Django 5+, Django REST Framework
- PostgreSQL (`psycopg2-binary`)
- JWT auth: `djangorestframework-simplejwt` (with token blacklist)
- API docs: `drf-spectacular` (OpenAPI / Swagger / Redoc)
- CORS: `django-cors-headers`
- Config: `python-dotenv`
- PDF generation: `reportlab` (invoice PDFs)

## Project structure

```
authproject/   Django project: settings.py, urls.py, wsgi/asgi
accounts/      Custom email-based User, password-reset tokens, auth endpoints, profile update, tests/
business/      Business domain
  models/        Business, Category, Product, StockMovement, Customer, Sale, SaleItem, Payment, Expense,
                 Invoice, InvoiceItem, InvoiceNumberSequence, Debt, DebtPayment
  serializers/   Request/response shapes
  views/         Endpoints
  services/      sale_service, payment_service, stock_service, product_service, business_service,
                 invoice_service, invoice_pdf, debt_service
  selectors/     dashboard, product, sale, debt and report queries
  permissions.py, utils.py (get_user_business), tests/
docs/          API reference and gap report
```

## Authentication

JWT (SimpleJWT). Log in / register to get `access` (30 min) and `refresh` (14 days) tokens, then send:

```
Authorization: Bearer <access_token>
```

Refresh tokens **rotate**: `POST /api/auth/token/refresh/` returns a new `access` **and** a new `refresh`;
the old refresh token is blacklisted and must not be reused. Logout blacklists the refresh token.
Full details: [`docs/API.md`](docs/API.md#authentication).

## API base URL

| Environment | Base URL |
|---|---|
| Local (browser / Postman) | `http://127.0.0.1:8000/` |
| Android emulator → PC | `http://10.0.2.2:8000/` |
| Physical device → PC | `http://<PC-LAN-IP>:8000/` (run `python manage.py runserver 0.0.0.0:8000`) |
| Production | HTTPS only (SRS requirement); URL to be provided by the backend team |

Route prefixes: `/api/auth/`, `/api/business/`.

## Swagger / OpenAPI

| URL | Description |
|---|---|
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | Redoc |
| `/api/schema/` | Raw OpenAPI schema |

> Every endpoint has request/response schemas. [`docs/API.md`](docs/API.md) adds the behaviour details
> (business rules, error shapes, known gaps).

## API modules

Authentication (+ profile update) · Business · Dashboard (today / week / month, plus a chart-series
endpoint) · Categories · Products (+ stock) · Customers (+ balance summary) · Sales · Payments · Expenses ·
Invoices (+ PDF, cancellation) · Debts (payable/receivable, payments, due-soon list) · Performance reports.
Every endpoint, request and response is documented in [`docs/API.md`](docs/API.md).

## Local setup

Requires Python 3.11+ and a running PostgreSQL.

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux / macOS

pip install -r requirements.txt

cp .env.example .env             # then edit .env (Windows: copy .env.example .env)
createdb BGroth                  # or create the database with pgAdmin

python manage.py migrate
python manage.py runserver
```

## Environment variables

Loaded from `.env` (git-ignored). Copy `.env.example` and fill in real values. **Never commit `.env`
or put real secrets in the README.**

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key | insecure placeholder (**must** be set outside development) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection | `BGroth`, `postgres`, *(empty)*, `localhost`, `5432` |
| `FRONTEND_RESET_PASSWORD_URL` | Link base in password-reset emails | placeholder URL |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | SMTP for password-reset emails | Gmail SMTP, no credentials |

## Android integration

- Base URL: see [API base URL](#api-base-url). `localhost` inside the emulator is the emulator itself,
  so use `10.0.2.2`.
- Plain `http://` needs a debug-only `network_security_config` on Android 9+. Use HTTPS in production.
- Send `Authorization: Bearer <access>` on every request except register, login, token refresh and
  password reset.
- After login call `GET /api/business/`. A **404** means the user has not created a business yet
  (show the business-setup screen); all other `/api/business/*` endpoints return 404 until then.
- Password-reset emails contain `FRONTEND_RESET_PASSWORD_URL?token=<uuid>`. For a mobile app this
  needs to be a deep link / App Link that opens the "new password" screen.

## API response / error handling

Errors are **not** in one uniform shape. A client must handle:

| Shape | Example | Where |
|---|---|---|
| Field errors | `{"email": ["..."]}` | serializer validation (400) |
| Non-field errors | `{"non_field_errors": ["..."]}` | login failure, "already have a business" (400) |
| `detail` | `{"detail": "Insufficient stock."}` | business-rule errors (400), 401, 404 |
| `error` | `{"error": "refresh token is required."}` | logout (400) |
| HTML (not JSON) | Django error page | unhandled server errors (500) while `DEBUG=True` |

Numbers: money is a JSON **string** (`"2.50"`); IDs are integers except `User.id` (UUID); datetimes are
ISO-8601 UTC. List endpoints return plain arrays; sales and expenses return a paginated envelope only when
`page` or `page_size` is sent. Search, ordering and date filters are in
[`docs/API.md`](docs/API.md#list-query-parameters).

## Testing

```bash
python manage.py test
```

211 tests: authentication flow (+ profile update), business, categories, products / stock / search / ordering,
customers and their balance summary, sales (payments, historical prices, date filters, ordering, pagination),
expenses, dashboard periods, invoices (creation, snapshot immutability, cancellation + reissue, PDF), debts
(validation, payments, due-date filtering), performance reports / chart series, the OpenAPI schema, and
cross-user data isolation. They need PostgreSQL access (Django creates and drops a `test_<DB_NAME>` database).

## Security notes

- Secrets come from environment variables. The DB password that used to be hard-coded in
  `settings.py` is still present in **git history** — rotate it (see gap report §H).
- Passwords are hashed by Django (PBKDF2). Login errors are generic. Password-reset requests always
  return the same message and are rate limited (5/hour per IP).
- Every business query is filtered by the authenticated user's business; cross-user access returned
  404 in manual tests.

## Production deployment notes

Before deploying: set `DEBUG=False`, restrict `ALLOWED_HOSTS` and CORS origins, set a strong
`DJANGO_SECRET_KEY`, serve over HTTPS, configure SMTP, use a dedicated DB user with a strong password,
and pin dependency versions. These are currently hard-coded in `authproject/settings.py`
(`DEBUG = True`, `ALLOWED_HOSTS = ["*"]`, `CORS_ALLOW_ALL_ORIGINS = True`).

## Known limitations / missing features

Not implemented (do not build UI against them yet): real push notifications/alerts (FCM or similar),
backup/restore, phone/email verification (OTP), product image upload, a `payment_status` filter on sales,
a payments list (a sale's payments can be recorded but not listed), and `DELETE` on a debt.
Remaining pre-Sprint-3 issues are listed in [`docs/GAP_REPORT.md`](docs/GAP_REPORT.md) (its invoices,
debts, reports and user-profile-update gaps are now closed).

## License

No license has been chosen yet (project ownership between the team members is not defined).
