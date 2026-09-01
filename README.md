# Auth API - Standalone Django Project for Authentication Only

A clean Django + DRF project with a single responsibility: register,
login, logout, and forgot/reset password via email. Designed to be
the backend for a mobile app (Kotlin or otherwise) via JWT.

## API Documentation (Swagger) - for the mobile team

| URL | Description |
|---|---|
| `http://127.0.0.1:8000/api/docs/` | Swagger UI - try out the endpoints directly from the browser |
| `http://127.0.0.1:8000/api/redoc/` | A more readable documentation view (Redoc) |
| `http://127.0.0.1:8000/api/schema/` | Raw OpenAPI schema file (.yaml) |

## Running the project

```bash
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   # optional - to log into /admin
python manage.py runserver
```

The API will be running at: `http://127.0.0.1:8000/api/auth/`

## Before deploying (Production)

1. Copy `.env.example` to `.env` and fill in `DJANGO_SECRET_KEY` with a long random value.
2. Change `DEBUG = False` and set `ALLOWED_HOSTS` in `authproject/settings.py`.
3. Replace `EMAIL_BACKEND` with real SMTP settings (already provided as a comment in the file).
4. Fill in `FRONTEND_RESET_PASSWORD_URL` with the real link or deep link
   that opens the "set a new password" screen in your app.

## Endpoints

| Method | Endpoint | Description | Requires token? |
|---|---|---|---|
| POST | `/api/auth/register/` | Register a new account | ❌ |
| POST | `/api/auth/login/` | Log in | ❌ |
| POST | `/api/auth/logout/` | Log out (blacklists the refresh token) | ✅ |
| POST | `/api/auth/token/refresh/` | Refresh the access token | ❌ (requires refresh token in the body) |
| GET  | `/api/auth/me/` | Current user's data | ✅ |
| POST | `/api/auth/change-password/` | Change password while logged in | ✅ |
| POST | `/api/auth/password-reset/request/` | Request a reset link via email | ❌ |
| POST | `/api/auth/password-reset/confirm/` | Confirm a new password using the token | ❌ |

### Request examples

**Register**
```json
POST /api/auth/register/
{
  "email": "user@example.com",
  "first_name": "Ahmad",
  "last_name": "Yousef",
  "password": "S3cure!Pass99",
  "password_confirm": "S3cure!Pass99"
}
```
Response: `{ "user": {...}, "tokens": { "access": "...", "refresh": "..." } }`

**Login**
```json
POST /api/auth/login/
{ "email": "user@example.com", "password": "S3cure!Pass99" }
```

**Using the access token** on any protected request:
```
Authorization: Bearer <access_token>
```

**Forgot password**
```json
POST /api/auth/password-reset/request/
{ "email": "user@example.com" }
```
→ Sends an email with a link shaped like: `FRONTEND_RESET_PASSWORD_URL?token=<uuid>`

```json
POST /api/auth/password-reset/confirm/
{
  "token": "<uuid-from-the-link>",
  "new_password": "NewPass123!",
  "new_password_confirm": "NewPass123!"
}
```

## Project structure

```
authproject/
├── manage.py
├── requirements.txt
├── .env.example
├── authproject/          # Global settings and routing
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── accounts/              # All authentication logic
    ├── models.py          # Custom email-based User + PasswordResetToken
    ├── serializers.py     # Validation for register/login/forgot password
    ├── views.py           # All endpoints
    ├── urls.py
    └── admin.py
```

## Security measures in place

- Passwords are hashed automatically (`set_password`) - never stored in plain text.
- The "invalid credentials" message is generic (doesn't reveal whether the email exists or the password is wrong).
- A password reset request always returns the same message (doesn't reveal whether the email is registered).
- Rate limiting on the password reset request (5 requests/hour per IP).
- The reset token is valid for a limited time and single-use only (`PASSWORD_RESET_TOKEN_LIFETIME_MINUTES`).
- The refresh token is blacklisted on logout.
