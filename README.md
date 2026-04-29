# Forge3D — Full-Stack 3D Asset Management Platform

A production-ready SaaS backend + fully integrated frontend for managing 3D assets
(`.glb`, `.obj`, `.usdz`, etc.) with JWT authentication, PostgreSQL via Supabase, and
direct-to-cloud file uploads.

---

## Project Structure

```
forge3D/
├── api/                        ← Flask backend
│   ├── app.py                  ← Entry point (Vercel serverless handler)
│   ├── requirements.txt
│   ├── schema.sql              ← Run in Supabase SQL editor
│   ├── .env.example            ← Copy → .env and fill in values
│   ├── utils/
│   │   ├── auth.py             ← JWT generation + require_auth decorator
│   │   └── db.py               ← psycopg2 connection pool (SSL enforced)
│   └── routes/
│       ├── auth_routes.py      ← POST /api/signup, /api/login, GET /api/me
│       ├── project_routes.py   ← CRUD for projects
│       ├── asset_routes.py     ← CRUD for assets
│       └── upload_routes.py    ← POST /api/upload-url (signed Supabase URL)
│
├── frontend/                   ← Vanilla HTML/JS (Tailwind CDN + Material Symbols)
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   ├── projects.html
│   ├── viewer.html             ← 3D viewer + file upload
│   ├── assets.html             ← Asset library
│   └── js/
│       ├── app.js              ← Shared shell (auth guard, sidebar, topbar, toast)
│       └── api.js              ← API client module (AuthAPI, ProjectsAPI, etc.)
│
├── vercel.json                 ← Vercel deployment config
└── .gitignore
```

---

## Quick Start (Local Development)

### 1. Set up environment

```bash
cd api
cp .env.example .env
# Fill in DATABASE_URL, JWT_SECRET, SUPABASE_URL, SUPABASE_SERVICE_KEY
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create database tables

Run `schema.sql` in your **Supabase SQL Editor** (Dashboard → SQL Editor → New Query).

### 4. Start the backend

```bash
cd api
python app.py
```
API runs at `http://localhost:5000`

### 5. Open the frontend

Open `frontend/login.html` in your browser, or serve it with any static server:

```bash
cd frontend
python -m http.server 3000
```
Then visit `http://localhost:3000/login.html`

---

## API Reference

### Authentication

| Method | Endpoint        | Body                        | Response                     |
|--------|-----------------|-----------------------------|------------------------------|
| POST   | `/api/signup`   | `{ email, password }`       | `{ token, user }`            |
| POST   | `/api/login`    | `{ email, password }`       | `{ token, user }`            |
| GET    | `/api/me`       | –                           | `{ user }`                   |

### Projects *(require `Authorization: Bearer <token>`)*

| Method | Endpoint               | Body          | Response           |
|--------|------------------------|---------------|--------------------|
| POST   | `/api/projects`        | `{ name }`    | `{ project }`      |
| GET    | `/api/projects`        | –             | `{ projects[] }`   |
| DELETE | `/api/projects/:id`    | –             | `{ message }`      |

### Assets *(require auth)*

| Method | Endpoint                       | Body                               | Response       |
|--------|--------------------------------|------------------------------------|----------------|
| POST   | `/api/assets`                  | `{ project_id, file_url, filename }`| `{ asset }`   |
| GET    | `/api/projects/:id/assets`     | –                                  | `{ assets[] }` |
| DELETE | `/api/assets/:id`              | –                                  | `{ message }`  |

### Upload

| Method | Endpoint          | Body                                          | Response                        |
|--------|-------------------|-----------------------------------------------|---------------------------------|
| POST   | `/api/upload-url` | `{ filename, project_id, content_type }`      | `{ upload_url, file_url, path }` |

**Upload flow:**
1. `POST /api/upload-url` → get signed URL
2. `PUT <file bytes>` → signed URL (direct to Supabase Storage, no auth header)
3. `POST /api/assets` → save metadata in DB

---

## Deploying to Vercel

1. Push to GitHub
2. Import repo in [vercel.com](https://vercel.com)
3. Add all `.env` keys as **Environment Variables** in the Vercel dashboard
4. Set **Root Directory** to `/` (root of repo)
5. Vercel reads `vercel.json` and routes `/api/*` to `api/app.py`

---

## Security

- Passwords hashed with **bcrypt** (12 rounds)
- JWTs signed with **HS256**, configurable expiry
- All project/asset routes verify **ownership** via user_id join
- Database uses **SSL** (`sslmode=require`)
- File type allowlist on both upload URL generation and asset metadata save
- Secrets loaded from environment variables only — never hardcoded
