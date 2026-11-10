# StockFlow MVP

StockFlow is a small, multi-tenant inventory management app. Each signup creates an organization and its single user; products and inventory settings are always scoped to the organization in the signed JWT.

## Stack

- **Frontend:** React 18, Vite, Tailwind CSS, React Router, Axios
- **Backend:** Python 3.10+, FastAPI, SQLAlchemy 2, Pydantic 2
- **Authentication:** JWT with `python-jose`; password hashing with `passlib` and bcrypt
- **Database:** SQLite locally; PostgreSQL when `DATABASE_URL` points to PostgreSQL
- **Hosting:** Render static site, web service, and managed PostgreSQL

## Project layout

```text
backend/
  app/
    main.py
    auth.py
    database.py
    models.py
    schemas.py
    routers/
      auth.py
      products.py
      dashboard.py
      settings.py
  tests/test_tenant_isolation.py
  requirements.txt
  .env.example
frontend/
  src/
    api/
    components/
    context/
    pages/
  .env.example
README.md
```

## Local setup

### Backend

In a terminal, from the project root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and set `SECRET_KEY` to a long, random value. The default database URL uses a local `stockflow.db` SQLite file. Start the API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`.

### Frontend

Open another terminal from the project root:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`). The frontend calls the backend at `http://localhost:8000` by default.

Run the backend tenant-isolation tests from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Create a production frontend bundle from `frontend/`:

```powershell
npm run build
```

## Environment variables

| Variable | Component | Required | Description |
|---|---|---:|---|
| `SECRET_KEY` | Backend | Yes | Secret used to sign access tokens. Use a unique long random value in production. |
| `DATABASE_URL` | Backend | No | SQLAlchemy database URL. Defaults to `sqlite:///./stockflow.db`; Render PostgreSQL URLs are supported. |
| `CORS_ORIGINS` | Backend | No | Comma-separated allowed browser origins. Defaults to `http://localhost:5173`. |
| `VITE_API_URL` | Frontend build | No | Backend origin without `/api`, e.g. `https://stockflow-api.onrender.com`. Defaults to `http://localhost:8000`. |

Do not commit `.env` files or production secrets. The checked-in `.env.example` files contain local-development defaults only.

## API endpoints

All application endpoints are under `/api`. Except for signup/login, endpoints require `Authorization: Bearer <token>`.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/signup` | Create an organization and its named user, then return a JWT |
| `POST` | `/api/auth/login` | Authenticate and return a JWT |
| `GET` | `/api/products` | List products; optional case-insensitive `search` query for name/SKU |
| `POST` | `/api/products` | Create a product |
| `GET` | `/api/products/{id}` | Get a product in the current organization |
| `PUT` | `/api/products/{id}` | Update a product in the current organization |
| `DELETE` | `/api/products/{id}` | Delete a product in the current organization |
| `PUT` | `/api/products/{id}/image` | Upload or replace product image (multipart field `image`) |
| `GET` | `/api/products/{id}/image` | Retrieve the product image |
| `DELETE` | `/api/products/{id}/image` | Remove the product image |
| `POST` | `/api/products/{id}/adjust` | Adjust stock with `{"delta": 1, "note": "Received stock"}` |
| `GET` | `/api/dashboard` | Product and unit totals plus low-stock products |
| `GET` | `/api/settings` | Read the organization's default low-stock threshold |
| `PUT` | `/api/settings` | Update with `{"default_low_stock_threshold": 5}` |
| `GET` | `/health` | Health check (no authentication required) |

Product SKUs are unique within an organization. Attempts to access a product owned by another organization return `404`.
Product images accept JPEG, PNG, GIF, or WebP up to 5 MB and are stored in the database, so they persist with the SQLite/PostgreSQL data. The image API uses the same JWT and tenant isolation as product records.

## Deploy to Render

1. Push the project to a Git provider connected to Render.
2. In Render, create a **PostgreSQL** database. Copy its **Internal Database URL** for the backend service.
3. Create a **Web Service** from the repository with:
   - Root directory: `backend`
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Environment variables: `DATABASE_URL` set to the PostgreSQL Internal Database URL; `SECRET_KEY` set to a generated secret; `CORS_ORIGINS` set to the final frontend site origin (for example `https://stockflow-ui.onrender.com`).
4. Create a **Static Site** from the same repository with:
   - Root directory: `frontend`
   - Build command: `npm install && npm run build`
   - Publish directory: `dist`
   - Environment variable: `VITE_API_URL` set to the backend origin without a trailing slash or `/api` (for example `https://stockflow-api.onrender.com`).
   - Rewrite rule: source `/*`, destination `/index.html`, action **Rewrite** (required for React Router routes).
5. Redeploy the static site after setting `VITE_API_URL`. Vite substitutes this variable at build time.
6. Confirm the backend `/health` responds with `{"status":"ok"}`, then sign up through the deployed frontend.

Tables are created automatically when the backend starts. For production, keep `SECRET_KEY` private and configure CORS to allow only the frontend origin.
