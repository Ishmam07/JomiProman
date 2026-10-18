# Deploy JomiProman: Vercel frontend + Railway API, MySQL and Redis

This preserves the existing React/Vite frontend, FastAPI backend, MySQL schema/triggers, Redis cache, AI, QR, ledger, and Admin Console. All seeded land records are fictional demo data.

## 0. Important prerequisite: push the source to GitHub

The repository is a monorepo. Ensure the source files are committed and pushed to `https://github.com/Ishmam07/JomiProman` before importing it. Never commit `.env`, `backend/data/ed25519.key`, API keys, DB passwords, or generated signing seeds.

## 1. Railway: create the backend and databases

1. Create a Railway project.
2. Add a MySQL database service named `MySQL` and a Redis service named `Redis` using `+ New` / `Database`.
3. Add a service from the GitHub repo `Ishmam07/JomiProman`.
4. In that backend service's Settings, set **Root Directory** to `/backend`. Railway will build `backend/Dockerfile`.
5. In the backend service's Variables, add the values below. Use Railway variable references exactly as shown; rename the references if you choose different service names.

```env
ENVIRONMENT=production
AUTO_SEED=true
DATABASE_URL=${{MySQL.MYSQL_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
GROQ_API_KEY=PASTE_YOUR_GROQ_KEY_HERE
GROQ_MODEL=openai/gpt-oss-120b
REGISTRAR_KEY=GENERATE_A_LONG_RANDOM_SECRET
ADMIN_KEY=GENERATE_A_DIFFERENT_LONG_RANDOM_SECRET
SIGNING_KEY_B64=GENERATE_A_BASE64_32_BYTE_SEED
CORS_ORIGINS=http://localhost:3100
PUBLIC_BASE_URL=http://localhost:3100
```

Generate the three secrets locally, do not paste them into chat or GitHub:

- `REGISTRAR_KEY`: `openssl rand -hex 32`
- `ADMIN_KEY`: run `openssl rand -hex 32` again (a different value)
- `SIGNING_KEY_B64`: `python3 -c 'import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())'`

Set `SIGNING_KEY_B64` once and keep it unchanged across deployments; it is the persistent Ed25519 signing seed. Do not also rely on an ephemeral container file for production signatures.

`AUTO_SEED=true` seeds fictional demo plots only when the database is empty. Keep it true for a demo deployment; set it false if you do not want fake records. This app is not connected to government land-record systems.

6. In Railway service Settings -> Networking, generate a public domain for the **backend only**. Do not enable public networking for MySQL or Redis; the backend uses private Railway service URLs.
7. In the backend's Settings -> Deploy, set the healthcheck path to `/api/health` if Railway has not detected it automatically.
8. Open `https://YOUR-RAILWAY-DOMAIN.up.railway.app/api/health`. A healthy response should report `status: ok` and `database: up`. `/api/docs` should also load.

## 2. Vercel: deploy the frontend

1. In Vercel, click **Add New -> Project** and import `Ishmam07/JomiProman` from GitHub.
2. Set **Root Directory** to `frontend`.
3. Framework preset: Vite. Build command: `npm run build`. Output directory: `dist` (defaults usually detect these).
4. Under Environment Variables, add `VITE_API_BASE` with the backend's public base URL followed by `/api`, e.g. `https://YOUR-RAILWAY-DOMAIN.up.railway.app/api`. This is a public URL, not a secret.
5. Deploy and copy the production frontend URL, e.g. `https://your-project.vercel.app`.

The `frontend/vercel.json` rewrite sends React Router deep links (`/plot`, `/register`, `/admin`, `/verify`, `/flagged`) to the SPA entry point.

## 3. Connect the final frontend URL to Railway CORS and QR links

After Vercel creates the production URL, edit the Railway backend variables:

```env
CORS_ORIGINS=https://YOUR-PROJECT.vercel.app
PUBLIC_BASE_URL=https://YOUR-PROJECT.vercel.app
```

If Vercel gives you a different production domain, use that exact origin (no trailing slash). Redeploy the Railway backend so the new variables take effect.

`PUBLIC_BASE_URL` is the frontend URL because QR codes should open the frontend `/verify` route, not the API server.

## 4. Smoke test

- Open the Vercel frontend.
- Open `https://YOUR-RAILWAY-DOMAIN.up.railway.app/api/health` and `/api/docs`.
- Check the home page and `Check before you buy` (`/plot?mouza=রহিমপুর&dag=412`).
- Check Register extraction using fictional sample deed text; inspect the AI/fallback badge.
- Verify a deed and its QR code.
- Open `/admin` and enter `ADMIN_KEY`; check the audit log.
- Confirm the browser console has no CORS errors.

## Notes / limitations

- Local MySQL data in Docker is not copied to Railway. Railway MySQL starts as a separate database. `AUTO_SEED=true` creates demo data there on first start.
- All seed records are fictional. Do not enter real citizen/deed data into a public demo without appropriate authorization and security review.
- The admin and registrar keys are prototype access controls, not a complete user/role authentication system.
- Keep `.env`, API keys and signing seeds out of GitHub. If any secret was ever committed or exposed, rotate it.
