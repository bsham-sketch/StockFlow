# StockFlow MVP

StockFlow is a small multi-tenant inventory app for tracking products, stock levels, and low-stock alerts. Each signup creates an organization with one user. Product and settings data are scoped to that user's organization.

## Features

- Organization signup, username, login, and JWT authentication
- Product create, list, search, update, and delete
- Optional image URL, product pricing, quantity, and per-product low-stock threshold
- Stock adjustments with protection against negative inventory
- Dashboard totals and low-stock alerts using organization defaults
- Organization-level default low-stock threshold

## Tech stack

- **Frontend:** React 18, Vite, Tailwind CSS, React Router, Axios
- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic
- **Authentication:** JWT (`python-jose`) and bcrypt (`passlib`)
- **Database:** SQLite locally; PostgreSQL on Render through `DATABASE_URL`
- **Deployment:** Render static site, web service, and managed PostgreSQL

## Local setup

### Backend

From the project root in PowerShell:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a long random `SECRET_KEY` in `backend/.env`, then run:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is at `http://localhost:8000`; interactive docs are at `http://localhost:8000/docs`.

### Frontend

Open another terminal at the project root:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). The frontend uses `VITE_API_URL` to connect to the backend.

### Seed demo data

With the backend environment configured, run from `backend/`:

```powershell
.\.venv\Scripts\python.exe seed.py
```

The script skips seeding if `demo@stockflow.com` already exists. The demo credentials are `demo@stockflow.com` / `Demo@1234`.

### Tests and production build

Run the tenant and validation tests from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Build the frontend from `frontend/`:

```powershell
npm run build
```

## Environment variables

| Variable | Component | Purpose |
|---|---|---|
| `SECRET_KEY` | Backend | Required JWT signing secret; use a unique secret in production. |
| `DATABASE_URL` | Backend | SQLAlchemy URL; defaults to `sqlite:///./stockflow.db`. PostgreSQL URLs using `postgres://` or `postgresql://` are converted to the psycopg driver. |
| `CORS_ORIGINS` | Backend | Comma-separated allowed frontend origins. `FRONTEND_URL` is accepted as a fallback. |
| `FRONTEND_URL` | Backend (optional fallback) | Frontend origin used only when `CORS_ORIGINS` is unset. |
| `VITE_API_URL` | Frontend build | Backend origin without `/api`, e.g. `https://stockflow-backend-7tki.onrender.com`. |

The checked-in `.env.example` files contain local-development values. Never commit `.env` files or production secrets.

## API endpoints

Except signup and login, endpoints require a bearer JWT in the `Authorization` header.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/signup` | Create an organization and its user, then return a JWT |
| `POST` | `/api/auth/login` | Authenticate and return a JWT |
| `GET` | `/api/products` | List products; optional case-insensitive `search` for name or SKU |
| `POST` | `/api/products` | Create a product |
| `GET` | `/api/products/{id}` | Get an organization-owned product |
| `PUT` | `/api/products/{id}` | Update an organization-owned product |
| `DELETE` | `/api/products/{id}` | Delete an organization-owned product |
| `POST` | `/api/products/{id}/adjust` | Adjust stock, e.g. `{"delta": 1, "note": "Received stock"}` |
| `GET` | `/api/dashboard` | Product/unit totals and low-stock products |
| `GET` | `/api/settings` | Read the organization's default low-stock threshold |
| `PUT` | `/api/settings` | Update the default low-stock threshold |
| `GET` | `/health` | Health check |

Product fields include name, SKU, description, quantity, cost and selling prices, low-stock threshold, and an optional image URL. SKU is unique within each organization.

## Render deployment

The live app is available at [StockFlow frontend](https://stockflow-frontend-iecj.onrender.com); the backend is [StockFlow API](https://stockflow-backend-7tki.onrender.com).

1. Create a managed PostgreSQL database on Render and copy its internal database URL.
2. Create a backend **Web Service** from the repository:
   - Root directory: `backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Set `DATABASE_URL` to the PostgreSQL URL, `SECRET_KEY` to a generated secret, and `CORS_ORIGINS` to `https://stockflow-frontend-iecj.onrender.com`.
3. Create a **Static Site** from the same repository:
   - Root directory: `frontend`
   - Build command: `npm install && npm run build`
   - Publish directory: `dist`
   - Set `VITE_API_URL` to `https://stockflow-backend-7tki.onrender.com`.
   - Add a rewrite rule from `/*` to `/index.html` with action **Rewrite** for React Router.
4. Deploy both services. Confirm the backend `/health` endpoint responds with `{"status":"ok"}`.

Demo login: `demo@stockflow.com` / `Demo@1234`. Run `backend/seed.py` against the deployment database to create this demo account and its sample products; the script skips if the account already exists.

Render's free tier may sleep while idle. The first request after sleeping can take about 50 seconds.

## How it works

The signed JWT identifies the user and organization. The backend obtains the organization from the authenticated user and applies it to product, dashboard, and settings queries; product IDs from other organizations are not found. Each product uses its own low-stock threshold when set, otherwise the organization's default. Quantity zero is shown as out of stock, and all products at or below their effective threshold appear on the dashboard.
