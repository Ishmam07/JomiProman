# JomiProman on Windows 10/11

This project can run on Windows using **Docker Desktop with the WSL 2 backend**. You do not need to install Python, Node.js, MySQL or Redis directly on Windows; Docker builds/runs those services in Linux containers.

## First-time setup

1. Install Docker Desktop for Windows: <https://www.docker.com/products/docker-desktop/>.
2. During setup, enable the WSL 2 backend. Start Docker Desktop and wait until it says the engine is running. If Docker asks to install/enable WSL, follow its instructions and restart Windows if requested.
3. Extract the complete JomiProman project ZIP to a normal folder, for example `C:\Users\YourName\Documents\jomi-proman`. **Open the folder that contains `docker-compose.yml`**—not its parent folder.
4. Double-click **`SETUP-Windows.bat`**. It creates `.env` from `.env.example` when needed, generates a private local `ADMIN_KEY`, validates Docker Compose, builds/starts the containers and waits for frontend/API health checks. The first build can take several minutes and requires internet access to download images/dependencies.
5. When setup succeeds, the browser opens automatically.

Alternatively, open PowerShell in the project root and run:

```powershell
.\setup-windows.ps1
```

## Local URLs

- Website: <http://localhost:3100>
- Admin panel: <http://localhost:3100/admin>
- API docs: <http://localhost:8101/api/docs>
- API health: <http://localhost:8101/api/health>
- MySQL for Workbench: `127.0.0.1:13306`
- Redis host port: `127.0.0.1:16379`

The admin key is kept in the local `.env` file. Retrieve it only on your machine from PowerShell with:

```powershell
Select-String '^ADMIN_KEY=' .env
```

Do not paste the key into chat, commit `.env`, or share it publicly. If you want live Groq AI rather than the built-in fallback, add your own key to `GROQ_API_KEY` in `.env`. The recommended default model in this package is `openai/gpt-oss-120b`. After editing `.env`, restart the backend:

```powershell
docker compose up -d --force-recreate backend
```

The project uses fictional demo records. The map coordinates are illustrative, and a local registration is not a government deed or official e-Mutation.

## Everyday use (double-click)

| File | Purpose |
|---|---|
| `START-JomiProman.bat` | Start the existing containers and open the website; does not rebuild images |
| `STOP-JomiProman.bat` | Stop the containers; **keeps database data** |
| `STATUS-JomiProman.bat` | Show container state and check API health |
| `LOGS-JomiProman.bat` | Follow backend/frontend/database logs; press `Ctrl+C` to stop viewing logs |
| `SETUP-Windows.bat` | First setup or rebuild images after code changes |

## Updating code

After pulling/copying newer project code, double-click `SETUP-Windows.bat` to rebuild and restart. For simple start/stop use the shortcuts above.

## Data safety

- Normal stopping uses `docker compose stop` and keeps all data.
- Rebuilding uses `docker compose up --build -d` and keeps named volumes.
- **Do not run `docker compose down -v` unless you intentionally want to delete the project's MySQL, Redis and signing-key volumes.**
- `.env` and `backend/data/*.key` must remain local and ignored by Git.

## Troubleshooting

**`docker` not found / cannot connect to Docker daemon**: the setup script tries to offer Docker Desktop installation through `winget`. If installation needs a restart, reboot, launch Docker Desktop, wait for the engine, then rerun `SETUP-Windows.bat`. If `winget` is missing, install Docker Desktop manually from the official site.

**A port is already in use**: edit the matching port in `.env` (`WEB_PORT`, `API_PORT`, `MYSQL_PORT`, or `REDIS_PORT`), then run `SETUP-Windows.bat` again. The defaults are chosen to avoid common conflicts.

**A service is unhealthy**: double-click `STATUS-JomiProman.bat`, then `LOGS-JomiProman.bat`, or run:

```powershell
docker compose ps
docker compose logs --tail=100 backend frontend mysql redis
```

**Database access denied after changing `.env`**: changing `MYSQL_PASSWORD` in `.env` does not update the password inside an already initialized MySQL volume. Do not delete volumes. Check logs and reconcile the MySQL app user's credentials safely.

**AI fallback is shown**: the app can operate without a Groq key. Check `GROQ_API_KEY`, `GROQ_MODEL`, internet connectivity, and backend logs if you expect live AI responses.

## Linux remains supported

Linux users can continue to run `chmod +x setup-linux.sh` and `./setup-linux.sh`.
