# AGENTS.md

## Cursor Cloud specific instructions

### Architecture

Two co-located services in one repo — see `QUICKSTART.md` for standard run commands:

| Service | Tech | Port | Entry |
|---------|------|------|-------|
| Frontend | Node/Express | 3000 | `server.js` |
| Backend | Python/FastAPI | 8000 | `backend/app/main.py` |

### Running services

**Backend** (from `backend/`):
```bash
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Frontend** (from repo root):
```bash
node server.js
```

The frontend proxies `/api/*` to the backend at `http://localhost:8000`.

### Environment variables

Railway secrets are injected automatically as system env vars in the Cloud Agent VM (including `DATABASE_URL`, `DATABASE_PUBLIC_URL`, `JWT_SECRET_KEY`, etc.). These override `backend/.env`. If you need to use SQLite locally instead of the Railway DB, you must explicitly pass `DATABASE_URL=sqlite:///./treemap.db` when starting uvicorn, because system env vars take precedence over `.env` files.

A minimal `backend/.env` is provided for local-only fallback:
```
DATABASE_URL=sqlite:///./treemap.db
ENVIRONMENT=development
JWT_SECRET_KEY=dev-secret-key-for-local-only
FRONTEND_BASE_URL=http://localhost:3000
MAGIC_LINK_DEV_LOG=true
```

### Testing

Backend tests: `cd backend && source venv/bin/activate && python -m pytest tests/ -v`

There is no frontend test suite or linter configured. There is no ESLint, Prettier, Ruff, or similar tool in the repo.

5 pre-existing test failures exist (Mock objects missing new fields like `ad_library_only`, `logo_url`, `header_color`, `tone_of_voice` on `ClientResponse`). These are not caused by environment setup.

### Auth for local testing

The app uses magic-link email auth. For local dev without Resend, set `MAGIC_LINK_DEV_LOG=true` and `ENVIRONMENT=development` — the magic link URL prints to the backend terminal instead of being emailed. Only approved domains can sign in (managed via founder admin).

### Gotchas

- `python3.12-venv` must be installed (`apt install python3.12-venv`) before creating the backend virtualenv.
- The frontend `server.js` reads `backend/.env` as a fallback for env vars like `BLOB_READ_WRITE_TOKEN`.
- The backend uses pydantic-settings which reads system env vars first, then `.env` — injected Railway secrets always win over the `.env` file.
