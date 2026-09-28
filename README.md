# Apna Hisab Kitaab — Backend (FastAPI)

FastAPI + SQLAlchemy 2 + JWT auth. SQLite by default, PostgreSQL by changing one setting.
All routes live under `/api/v1`. Interactive docs: **http://127.0.0.1:8000/docs**

## Run (Windows)

Double-click **`run.bat`** (or run it in the VS Code terminal from this folder).
First run creates `.venv` and installs packages; after that it starts in seconds.

Manual way:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Needs **Python 3.11+**. Tables are created automatically on startup.
Demo account (created on startup while `SEED_DEMO=true`): **ayesha@example.pk / demo1234**.

## Run with Docker + PostgreSQL

From the project root: `docker compose up --build` → API on http://localhost:8000.

## Settings (`backend/.env`, see `.env.example`)

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./apna_hisab.db` | PostgreSQL: `postgresql+psycopg://user:pass@host:5432/db` |
| `JWT_SECRET` | dev value | **Change in production** |
| `JWT_EXPIRES_DAYS` | 30 | Login stays valid this long |
| `CORS_ORIGINS` | localhost:5173 | Add your deployed frontend URL |
| `TIMEZONE` | Asia/Karachi | Defines "today" for totals |
| `SEED_DEMO` | true | Set `false` in production |

## Endpoints

| Area | Routes |
|---|---|
| Auth | `POST /auth/signup` · `POST /auth/login` · `POST /auth/forgot-password` · `POST /auth/reset-password` · `POST /auth/change-password` |
| Account | `GET/PATCH/DELETE /me` · `GET /export` |
| Expenses | `GET /expenses` (search, category_id, from, to, min_amount, max_amount, sort, page, page_size) · `POST /expenses` · `PATCH/DELETE /expenses/{id}` · `DELETE /expenses` (clear all) · `GET /expenses/suggestions` |
| Categories | `GET/POST /categories` · `PATCH/DELETE /categories/{id}` (expenses move to "Other") |
| Budget | `GET /budgets/current` · `PUT /budgets/{year}/{month}` |
| Insights | `GET /dashboard/stats` · `GET /analytics?from&to&granularity` · `GET /reports?from&to&title` · `GET /reports/export?format=pdf\|excel\|csv` |

Every user only ever sees their own data. Passwords are bcrypt-hashed. Amounts are whole rupees.

## Tests

```bash
pip install -r requirements.txt
pytest
```

## Not included yet

- **Email sending** for "Forgot password": the reset link is printed in the server console.
  Add an SMTP/email provider in `routers/auth.py → forgot_password` to email it.
- **Database migrations** (Alembic): tables are created with `create_all`. Add Alembic before changing
  columns on a live database.
