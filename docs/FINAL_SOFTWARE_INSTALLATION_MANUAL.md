# ApplyWise
## Software Installation Manual
COSC 6370 — Advanced Software Engineering  
Team Islanders  
Version 2.0 — Final Submission, November 2026

### 1. Purpose and Scope
This manual explains how to install, configure, run, and verify ApplyWise locally for final project evaluation. ApplyWise is a web-based resume customization and job-application assistant. Its central rule is that generated statements must be grounded in user-reviewed and approved career evidence.

This final installation uses SQLite, not PostgreSQL. The included `apps/api/local_setup.py` script creates the local database and demo account. Docker, a paid AI API key, and an external service account are not required. These instructions concern local evaluation, not production hosting.

### 2. System Requirements
| Component | Required version | Purpose |
| --- | --- | --- |
| Python | 3.12 or newer | Backend API, SQLite setup, backend tests |
| Node.js and npm | Node.js 20 or newer | React/Vite frontend and tests |
| ZIP extraction utility | Operating-system standard | Extract the source archive |
| Web browser | Current version | Evaluate the application |

Allow local network ports 8000 for the backend and 5173 for the frontend. Confirm versions using `python --version`, `node --version`, and `npm --version`.

### 3. Installation
Perform these steps in order. Keep the backend and frontend terminals open while evaluating ApplyWise.

**Step 1. Extract the source archive.** Extract `COSC6370_Team_Islanders_Team_Project_Source_Code.zip` into a new folder. Open the extracted repository root; it contains `apps/api`, `apps/web`, and `README.md`.

**Step 2. Create the Python virtual environment.** On Windows PowerShell, from the repository root:

```powershell
cd apps\api
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt with `.venv\Scripts\activate.bat`. On macOS or Linux:

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
```

**Step 3. Install backend dependencies.** From `apps/api`, with the environment active:

```bash
python -m pip install -e ".[dev]"
```

**Step 4. Prepare the environment file.** Copy `apps/api/.env.example` to `apps/api/.env`. With the terminal still inside `apps/api`, run the operating-system-specific commands.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
$env:DATABASE_URL = "sqlite:///./local.db"
```

Windows Command Prompt:

```bat
copy .env.example .env
set DATABASE_URL=sqlite:///./local.db
```

macOS/Linux:

```bash
cp .env.example .env
export DATABASE_URL=sqlite:///./local.db
```

The terminal DATABASE_URL setting is necessary because `local_setup.py` reads it directly from the process environment; copying `.env` alone does not set it for that script. Keep `APP_ENV=development` and `AI_PROVIDER=stub`. Do not commit real secrets or an `.env` file.

**Step 5. Create the SQLite database and demo account.** From `apps/api`, using the same terminal:

```bash
python local_setup.py --seed
```

This creates `apps/api/local.db`, application tables, one demo user, and four approved evidence records. Do not run `alembic upgrade head`: the Alembic sequence is for PostgreSQL and does not migrate this SQLite setup.

**Step 6. Start the backend.** From `apps/api`, in the same terminal:

```bash
python -m uvicorn app.main:app --reload
```

Keep it running at `http://localhost:8000`.

**Step 7. Start the frontend.** Open a second terminal in the project root:

```bash
cd apps/web
npm install
npm run dev
```

Open the site at `http://localhost:5173`. Vite proxies API requests to port 8000.

### 4. Verifying the Installation
1. Open `http://localhost:8000/health`; the expected response is `{"status":"ok","service":"applywise-api","version":"0.1.0"}`.
2. Open `http://localhost:8000/docs`; API documentation should load in development mode.
3. Open `http://localhost:5173`; the ApplyWise sign-in screen should appear.

### 5. First Use
Use the seeded local evaluation account:

| Field | Value |
| --- | --- |
| Email address | `demo@example.edu` |
| Password | `demopass123` |

Follow the guided application journey, inspect the four approved evidence records, paste a job description, review generated candidate statements with their cited evidence, and save a reviewed draft to an application. The `stub` provider deliberately produces predictable, offline responses rather than live AI-generated output. The optional `anthropic` provider needs an external API key and is not required.

### 6. Stopping and Restarting the Application
Press Ctrl+C in the frontend terminal, then Ctrl+C in the backend terminal. No Docker commands are involved. The `apps/api/local.db` file preserves demo data between runs.

To restart, activate the existing virtual environment, set `DATABASE_URL=sqlite:///./local.db` again in the backend terminal, start Uvicorn, and start Vite in the frontend terminal. To deliberately reset the demo, stop the API, remove `apps/api/local.db`, and rerun `python local_setup.py --seed`. This deletes prior local data.

### 7. Running the Automated Tests
Backend commands from `apps/api` with the environment active:

```bash
python -m pytest -q
python -m ruff check .
```

Frontend commands from `apps/web`:

```bash
npm test -- --run
npx tsc --noEmit
npm run lint
npm run build
```

These commands should complete without errors for a clean submission. Investigate any failures; do not describe tests as passing unless they have been executed.

### 8. Troubleshooting
| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| Python installation fails | Python older than 3.12 or inactive environment | Install Python 3.12+ and activate .venv |
| PowerShell blocks activation | Execution policy | Use Command Prompt and activate.bat |
| DATABASE_URL not set | The setup script does not load .env by itself | Run the terminal-specific DATABASE_URL command in Step 4 |
| Setup script rejects database engine | PostgreSQL URL remains in environment | Set DATABASE_URL to sqlite:///./local.db |
| SQLite reports missing tables | Local schema setup skipped | Stop API; rerun local_setup.py --seed |
| Port 8000 in use | Another process binds the backend port | Stop conflicting process |
| Frontend cannot contact API | Backend stopped | Check /health and restart Uvicorn |
| npm install fails | Node version or dependencies | Install Node.js 20+ and rerun npm install |
| Demo login fails | Seeder did not complete or incorrect DB | Check local.db and rerun --seed |
| AI responses are repetitive | Stub provider is selected | This is expected for offline evaluation |

### 9. Reference Information
| Service or file | Address or location |
| --- | --- |
| Web interface | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Health check | http://localhost:8000/health |
| API reference | http://localhost:8000/docs |
| SQLite database | apps/api/local.db |
| Local configuration example | apps/api/.env.example |
| Local setup script | apps/api/local_setup.py |

The source package includes the tracked repository source, this manual in Word and PDF, and the files under `docs`. Runtime/generated content such as `.env`, `.git`, `.venv`, `node_modules`, and `local.db` is not included.

Team repository: https://github.com/Nithin0553/ApplyWise
