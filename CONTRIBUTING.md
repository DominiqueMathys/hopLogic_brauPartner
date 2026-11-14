# Mitarbeit

Änderungen laufen über Branches und Pull Requests. Direkte Commits auf `main` sind für die gemeinsame Arbeit nicht vorgesehen.

## Branches

- `main` enthält den stabilen Stand.
- `feature/*` enthält eine neue Funktion, zum Beispiel `feature/partner-filter`.
- `fix/*` enthält eine Fehlerbehebung, zum Beispiel `fix/order-vat`.

## Ablauf

1. Das Repository klonen: `git clone https://github.com/DominiqueMathys/hopLogic_brauPartner.git`.
2. Die Installation aus der [README](README.md) ausführen, inklusive `.env`, Migration und `npm ci`.
3. Einen Branch vom aktuellen `main` erstellen: `git switch -c feature/kurze-beschreibung`.
4. Die Änderung lokal mit pytest und, bei Oberflächenänderungen, mit `npm run lint` und `npm run build` prüfen.
5. Nur die zugehörigen Dateien stagen. `.env`, `data/local-dev-access.txt`, `data/mock-erp.sqlite`, `.venv` und `node_modules` nicht hinzufügen.
6. Eine Commit-Nachricht schreiben, die den Grund der Änderung nennt.
7. Den Branch mit `git push -u origin HEAD` auf GitHub legen.
8. Einen Pull Request gegen `main` öffnen. Die Vorlage fragt nach dem Umfang und den ausgeführten Tests.
9. Eine andere Person liest den Pull Request. Erst danach wird er zusammengeführt.

## Review

Der Review prüft fachliche Wirkung, Berechtigungen, Migrationen und ob Demo-Daten fiktiv bleiben. Secrets, Dumps und lokale Datenbankdateien werden nicht übernommen.

GitHub-Rechte und die Sichtbarkeit des Repository werden nicht aus dem Code heraus geändert.
