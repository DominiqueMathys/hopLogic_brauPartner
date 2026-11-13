# Datenbank

PostgreSQL 16 wird über den Dienst `db` in `docker-compose.yml` bereitgestellt. Das Datenverzeichnis liegt im Docker-Volume `postgres_data` und gehört nicht ins Repository.

Das relationale Schema entsteht mit Alembic unter `backend/alembic/`. Die Verbindung konfiguriert `DATABASE_URL` beziehungsweise die Variablen `POSTGRES_USER`, `POSTGRES_PASSWORD` und `POSTGRES_DB`.

Dieses Verzeichnis nimmt später optionale, geheimnisfreie Initial- oder Seed-Skripte auf. Zugangsdaten und Datenbankdumps bleiben ausserhalb von Git.
