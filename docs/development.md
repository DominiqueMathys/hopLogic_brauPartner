# Entwicklung

Die alltägliche Arbeit geht vom Projektverzeichnis `hopLogic_brauPartner` aus. Befehle für Git gehören in dieses Verzeichnis, damit sie das Repository des übergeordneten Benutzerordners nicht betreffen.

## Täglicher Start

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Nach Codeänderungen im Image genügt ein erneutes `docker compose up --build`. `docker compose up` ohne `--build` startet die zuletzt gebauten Images.

Für automatisches Neuladen der API kann der Backend-Dienst mit `UVICORN_RELOAD=1` gestartet werden. Dafür muss der Container den lokalen Quelltext eingehängt bekommen. Der mitgelieferte Compose-Aufbau startet den jeweils gebauten Stand und hält den ersten Start dadurch vorhersehbar.

## Lokal ohne Docker

Dafür müssen Python 3.12, Node.js 22 und ein erreichbares PostgreSQL mit den Werten aus `.env` bereitstehen.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\alembic.exe -c backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In einem zweiten Terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Die Oberfläche liegt danach auf http://localhost:5173, die API auf http://localhost:8000.

## Tests

```powershell
.\scripts\test.ps1
```

Oder direkt:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Im Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

Die Workflow-Datei `.github/workflows/ci.yml` führt dieselben Prüfungen auf GitHub Actions aus, sobald das Repository dort liegt.

## Schema erweitern

1. Modell in `backend/app/models/` anlegen.
2. Das Modul in `backend/app/models/__init__.py` importieren.
3. Im Projektverzeichnis eine Migration erzeugen:

```powershell
.\.venv\Scripts\alembic.exe -c backend\alembic.ini revision --autogenerate -m "fachliches modell"
.\.venv\Scripts\alembic.exe -c backend\alembic.ini upgrade head
```

Im Container übernimmt `backend/entrypoint.py` den Upgrade-Schritt beim Start.

## Neue API-Routen

Routen kommen als Router unter `backend/app/api/` und werden in `backend/app/main.py` mit einem Präfix eingebunden. Antwortmodelle liegen unter `backend/app/schemas/`. Die bestehende Health-Route zeigt das Muster.

## Umgebungsvariablen

| Variable | Bedeutung |
| --- | --- |
| `POSTGRES_USER` | Datenbankbenutzer im Container |
| `POSTGRES_PASSWORD` | Datenbankpasswort im Container |
| `POSTGRES_DB` | Datenbankname |
| `DATABASE_URL` | SQLAlchemy-URL für den Start ausserhalb von Docker |
| `ENVIRONMENT` | Name der Laufumgebung |
| `CORS_ORIGINS` | Kommagetrennte erlaubte Origins |
| `API_PROXY_TARGET` | Ziel des Vite-Proxys, nur für den Frontend-Prozess |
| `DEV_SERVER_HOST` | Bind-Adresse des Vite-Servers |

`.env` wird von Docker Compose für die Variablenersetzung gelesen und zusätzlich in den Backend-Container gegeben. `DATABASE_URL` setzt Compose für den Container neu, damit der Hostname `db` verwendet wird.
