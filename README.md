# HopLogic BrauPartner

CRM-Grundlage für das Liechtensteiner Brauhaus im FHGR-Modul Digital Relationship Management.

Diese erste Phase stellt die technische Basis bereit: eine React-Oberfläche, eine FastAPI-Schnittstelle und PostgreSQL. Die Oberfläche prüft beim Start, ob API und Datenbank erreichbar sind. Die fachlichen CRM-Module bauen in den nächsten Phasen auf dieser Struktur auf.

## Voraussetzungen

- Docker Desktop mit Docker Compose v2
- Git
- Für Tests und die Entwicklung ohne Container: Python 3.12 und Node.js 22

## Start mit Docker Compose

Im Projektverzeichnis:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Dasselbe erledigt `.\scripts\start.ps1`. Das Skript legt `.env` aus der Vorlage an, falls die Datei noch fehlt.

Danach sind die Dienste unter diesen Adressen erreichbar:

| Dienst | Adresse |
| --- | --- |
| Oberfläche | http://localhost:5173 |
| API | http://localhost:8000 |
| API-Dokumentation | http://localhost:8000/docs |
| API-Health | http://localhost:8000/api/health |
| Datenbank-Health | http://localhost:8000/api/health/db |
| PostgreSQL | localhost:5432 |

Die Oberfläche ruft `/api/health` und `/api/health/db` auf. Im Container leitet Vite diese Pfade an den Backend-Dienst weiter. Beide Karten stehen auf **Erreichbar**, wenn Oberfläche, API und Datenbank verbunden sind.

Beenden im laufenden Terminal mit `Ctrl+C`. In einem zweiten Terminal stoppt `docker compose down` die Dienste. Datenbankdaten bleiben im Docker-Volume `postgres_data` erhalten.

## Tests

```powershell
.\scripts\test.ps1
```

Die Tests laufen ohne PostgreSQL. Sie prüfen die API-Antworten und eine simulierte Datenbankprüfung. Interne Fehlerdetails, etwa Verbindungsdaten, verlassen die API dabei nicht.

Frontend prüfen:

```powershell
cd frontend
npm ci
npm run lint
npm run build
```

## Zugangsdaten

Lokale Werte stehen in `.env`. Diese Datei bleibt ausserhalb von Git. `.env.example` enthält Platzhalter für die eigene Entwicklungsumgebung. Produktive Zugangsdaten werden hier nicht abgelegt.

Passwörter in `DATABASE_URL` bleiben URL-sicher: Buchstaben, Ziffern und Bindestrich. Docker Compose setzt für den Backend-Container eine eigene URL mit dem Hostnamen `db`.

## Projektstruktur

```text
frontend/    React, TypeScript, Vite, Tailwind CSS
backend/     FastAPI, SQLAlchemy, Alembic
database/    Hinweise zur PostgreSQL-Datenhaltung
tests/       Automatisierte API-Tests
docs/        Architektur und Entwicklungsablauf
scripts/     Start- und Testskripte
.github/     Continuous Integration
```

## Git

Das Repository gehört ausschliesslich in dieses Projektverzeichnis. Es gibt noch keinen Commit und kein Remote.

## Weitere Dokumentation

- [Architektur](docs/architecture.md)
- [Entwicklung](docs/development.md)
- [Datenbank](database/README.md)
