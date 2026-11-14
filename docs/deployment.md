# Bereitstellung

Diese Anwendung ist für die lokale Entwicklung und eine kontrollierte Demo beschrieben. Ein öffentliches Deployment wurde nicht ausgeführt. Die Anwendung ist nicht produktiv freigegeben.

## Umgebungen

| Umgebung | Zweck | Daten |
| --- | --- | --- |
| Lokale Entwicklung | Tägliche Arbeit auf dem eigenen Rechner | Eigene PostgreSQL-Datenbank, fiktive Demo-Daten erlaubt |
| Test | pytest und GitHub Actions | Eigene Datenbank, wird von den Tests nicht als Demo behalten |
| Demo | Geführte Vorstellung | Eigene Datenbank, nur fiktive Daten, Zugang begrenzt |
| Produktion | Nicht eingerichtet | Keine Demo-Daten, keine Secrets im Repository |

`ENVIRONMENT=development` erlaubt Demo-Konten beim Bootstrap. In Demo und Produktion `CREATE_DEMO_USERS=0` setzen und das Seed nicht gegen die Zieldatenbank laufen lassen.

## Lokale Bereitstellung

Siehe die Startanleitung in der [README](../README.md). PostgreSQL muss vor der API erreichbar sein. `alembic upgrade head` legt das Schema an und erhält vorhandene Zeilen.

Prüfadressen:

- http://127.0.0.1:8000/api/health
- http://127.0.0.1:8000/api/health/db
- http://127.0.0.1:5173

## Demo mit Docker Compose

`docker compose up --build` startet PostgreSQL, API, Oberfläche und den Worker. Die API wartet auf den Healthcheck der Datenbank, führt die Migration aus und gilt erst als bereit, wenn `/api/health/db` antwortet. Die Oberfläche startet danach. Das Volume `postgres_data` bleibt bei `docker compose down` erhalten. `docker compose down -v` löscht dieses Volume und damit die Datenbank. Diesen Befehl nicht gegen eine Datenbank mit behaltenswerten Daten verwenden.

Auf dem Rechner dieser Prüfung war der Befehl `docker` nicht vorhanden. Der Containerstart wurde nicht ausgeführt.

## Umgebungsvariablen

| Variable | Bedeutung |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy-URL zu PostgreSQL |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Werte für den Datenbank-Container |
| `ENVIRONMENT` | `development` nur für die lokale Arbeit |
| `CORS_ORIGINS` | Erlaubte Oberflächenadressen, kommagetrennt |
| `SESSION_COOKIE_SECURE` | Lokal über HTTP `false`, hinter HTTPS `true` |
| `MOCK_ERP_PATH` | Pfad der SQLite-Testdatei |
| `ERP_TIMEOUT_SECONDS`, `ERP_MAX_ATTEMPTS` | Grenzen für einen späteren Connector |
| `ERP_BASE_URL`, `ERP_CLIENT_ID`, `ERP_CLIENT_SECRET` | Leer lassen, bis ein echter Connector existiert |
| `AUTOMATION_EMBEDDED_WORKER` | Im Container `false`, der Dienst `worker` übernimmt die Läufe |
| `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD` | Nur beim ersten Administrator, nicht versionieren |
| `CREATE_DEMO_USERS` | `0` ausserhalb der Entwicklung |

Passwörter in `DATABASE_URL` bleiben URL-sicher: Buchstaben, Ziffern und Bindestrich.

## Sicherheit

- Sitzungs-Cookie `bp_session` ist HTTP-only. Das CSRF-Cookie wird bei schreibenden Aufrufen als Header erwartet.
- Passwörter werden mit scrypt gehasht. Sitzungs- und Reset-Token liegen nur als SHA-256-Hash in der Datenbank.
- Hinter einem öffentlichen Host HTTPS verwenden und `SESSION_COOKIE_SECURE=true` setzen.
- CORS auf die konkrete Oberflächenadresse begrenzen.
- Die fünf Fehlversuche je Konto ersetzen kein vorgelagertes Rate-Limiting eines Reverse-Proxys.
- Anhänge und Exporte bleiben hinter der Anmeldung und der Rollenprüfung.
- Secrets gehören in den Secret-Speicher der Umgebung, nicht in Git.

## Sicherung und Wiederherstellung

PostgreSQL regelmässig mit `pg_dump` sichern. Die Sicherung ausserhalb des Repository und ausserhalb des Datenbankservers lagern. Wiederherstellen heisst: leere Datenbank anlegen, Dump einspielen, `alembic upgrade head` nur ausführen, wenn der Dump ein älteres Schema enthält. Zusätzlich das Verzeichnis `data/ticket-attachments` sichern. Die Mock-SQLite-Datei ist Testdaten und kein Backup des CRM.

Vor einem Restore die Anwendung stoppen, damit keine halben Schreibvorgänge laufen.

## Monitoring und Logs

Für eine Demo genügen die Health-Routen und die Container-Healthchecks von Datenbank, API und Oberfläche. Der Worker hat keinen eigenen HTTP-Port. Sein Log zeigt, wie viele fällige Läufe geprüft wurden. API-Logs dürfen keine Passwörter, Tokens oder ERP-Secrets enthalten. Die aktuelle Anwendung schreibt solche Werte nicht in ein Anwendungs-Log.

Ein Produktivbetrieb bräuchte zusätzlich eine feste Aufbewahrung der Logs, Alarm bei fehlgeschlagenen Healthchecks und eine benannte verantwortliche Person. Das ist hier nicht eingerichtet.
