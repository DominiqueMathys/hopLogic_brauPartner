# HopLogic BrauPartner

CRM-Webanwendung für das FHGR-Projekt «HopLogic BrauPartner» des Liechtensteiner Brauhauses.

Die Anwendung verbindet eine React-Oberfläche mit einer FastAPI-Schnittstelle und PostgreSQL. Sie umfasst Vertriebspartner, Kontakte, Aktivitäten, Aufgaben, Verkaufschancen, Produkte, Bestellungen, Kundenservice, Marketing, Automatisierungen, Festmanagement mit Festmaterial, Reporting, Anmeldung mit Rollen und eine ERP-Testintegration. Das Mock-ERP ist eine lokale Testdatenbank mit fiktiven Daten. Es ist keine Verbindung zum ERP des Liechtensteiner Brauhauses.

Die Anwendung ist für die lokale Entwicklung, automatisierte Tests und eine kontrollierte Demo vorbereitet. Sie ist damit nicht als produktiv freigegeben.

## Technologiestack

- Frontend: React, TypeScript, Vite, Tailwind CSS, React Router
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- Datenbank: PostgreSQL 16
- Tests: pytest
- Container: Docker Compose, sofern Docker lokal vorhanden ist

## Voraussetzungen

- Python 3.12
- Node.js 22
- Ein erreichbares PostgreSQL 16
- Git
- Docker Desktop mit Compose v2, wenn die Anwendung in Containern laufen soll

## Installation

Im Projektverzeichnis:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
cd frontend
npm ci
```

`.env` bleibt ausserhalb von Git. Die Werte in `.env.example` sind Platzhalter für die eigene Entwicklungsumgebung.

## Start

API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Oberfläche, in einem zweiten Terminal:

```powershell
cd frontend
npm run dev
```

Die Oberfläche liegt auf http://127.0.0.1:5173 und leitet `/api` an http://127.0.0.1:8000 weiter. Die API-Dokumentation liegt auf http://127.0.0.1:8000/docs.

Mit Docker, sofern der Befehl `docker` verfügbar ist:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Dieselbe Vorbereitung erledigt `.\scripts\start.ps1`. In dieser Entwicklungsumgebung war Docker nicht installiert. Der Containerstart wurde deshalb hier nicht ausgeführt.

## Demo-Zugang

Den ersten Administrator legt dieser Befehl an, solange noch kein reales Administratorkonto existiert:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.bootstrap_admin
```

Das Passwort wird nur in die gitignorierte Datei `data/local-dev-access.txt` geschrieben. Es gehört nicht ins Repository und nicht in die Dokumentation. Demo-Konten entstehen nur, wenn `ENVIRONMENT` auf `development` steht. Für eine andere Umgebung `CREATE_DEMO_USERS=0` setzen.

Fiktive CRM-Daten laden die Skripte unter `scripts\`. Sie sind wiederholbar und erzeugen keine Dubletten. Ein erneutes Laden darf eine bereits übertragene Demo-Bestellung nicht unbedacht zurücksetzen. Die Skripte deshalb nicht gegen eine Datenbank ausführen, deren Demo-Ablauf erhalten bleiben soll.

Das fiktive Fest «Sommerfest am See 2027» lädt dieser Befehl. Er ist wiederholbar und verändert keine bestehenden Bestellungen:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.seed_festivals
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run lint
npm run build
```

`.\scripts\test.ps1` installiert die Python-Abhängigkeiten und startet pytest. Die Tests brauchen die PostgreSQL-Datenbank aus `.env`. Schreibende Tests laufen in einer Transaktion, die am Ende zurückgerollt wird.

## Projektstruktur

```text
frontend/     React-Oberfläche
backend/      FastAPI, Modelle, Migrationen, Mock-ERP
tests/        pytest
database/     Hinweise zur PostgreSQL-Haltung
docs/         Architektur, Nutzung, Tests, Bereitstellung
scripts/      Start und Testdaten
.github/      CI und Vorlagen für Issues und Pull Requests
```

## Weitere Dokumentation

- [Architektur](docs/architecture.md)
- [Benutzung](docs/user-guide.md)
- [Entwicklung und GitHub](docs/development.md)
- [Tests](docs/testing.md)
- [Bereitstellung](docs/deployment.md)
- [Mitarbeit](CONTRIBUTING.md)
