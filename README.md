# Graeter

## NB Delivery Dispatch — first working release

Restaurant delivery planning with a Next.js dashboard, FastAPI service, OR-Tools optimisation and transactional dispatch. **Simulation is clearly labelled; this release is not yet production-ready.** See [verification and unfinished features](docs/STATUS.md).

### Start with Docker Compose

Requires Docker Compose. From this branch:

```bash
cp .env.example .env
# Edit .env: set unique SESSION_SECRET (32+ characters), DEMO_PASSWORD (12+), POSTGRES_PASSWORD.
docker compose up --build
```

Open http://localhost:3000. Demo accounts: `manager`, `dispatcher`, `driver1`, `driver2`, all using your chosen demo password. The migration job seeds an empty database once. Data is preserved in a named PostgreSQL volume. Database and API ports are not publicly exposed.

Compose is supplied but could not be run in the development environment because Docker was unavailable.

### Run locally without Docker

Python 3.12+, Node 24+, npm. SQLite is the default local database. Use a virtual environment and set secrets in your shell (or through your environment manager); `.env` is consumed by Compose, not automatically by Python.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r services/api/requirements.txt
export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
# Set DEMO_PASSWORD to your own password, at least 12 characters.
export DEMO_PASSWORD='choose-a-long-local-demo-password'
cd services/api
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --reload --port 8000
```

In a second terminal at repository root:

```bash
npm ci --prefix apps/web
npm run dev --prefix apps/web
```

Open http://localhost:3000. API documentation: http://localhost:8000/docs. The Next.js proxy uses `API_INTERNAL_URL`, default `http://127.0.0.1:8000`. Windows users can use WSL or equivalent PowerShell environment-variable commands.

### Verify

```bash
python -m pytest -q
npm test --prefix apps/web
npm run build --prefix apps/web
python scripts/smoke.py
```

The smoke test launches disposable API/web processes on ports 8000 and 3000; stop existing processes on those ports first. It executes real HTTP requests through Next.js, uses a temporary database, and deletes it afterwards. It is not a browser test.

### Structure

- `services/api/app/domain.py` — validated domain contracts.
- `routing.py` — deterministic directed demo graph and Google matrix adapter.
- `optimisation.py` — bounded route generation, OR-Tools selection, safe fallback.
- `db.py`, `main.py` — persistence, roles, proposals and atomic trip lifecycle.
- `apps/web` — operational dashboard and mobile driver view.
- `docs/requirements.md` — original master specification.
- [Architecture and decisions](docs/ARCHITECTURE.md), [operator/setup guide](docs/OPERATIONS.md), [verification and gaps](docs/STATUS.md).

The original `# Graeter` heading is preserved. All implementation is on a development branch; `main` is unchanged.
