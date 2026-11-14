# Tests

## Strategie

Die fachlichen Module werden über die HTTP-API geprüft. Jeder Test öffnet eine Datenbanktransaktion und rollt sie am Ende zurück. Persistenztests schreiben bewusst und stellen den vorherigen Stand der berührten Demo-Zeilen wieder her. Sie löschen keine vorhandenen Partner oder Aufgaben.

Browserprüfungen der einzelnen Phasen sind manuell gelaufen. Eine Playwright-Suite ist nicht eingerichtet und wurde in dieser Abschlussprüfung nicht ausgeführt. Der durchgängige Ablauf liegt stattdessen als HTTP-Test in `tests/test_workflow.py`.

## Automatisiert ausführen

```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run lint
npm run build
```

GitHub Actions verwendet dieselbe Aufteilung. Der Workflow `.github/workflows/ci.yml` startet PostgreSQL 16 als Dienst, führt `alembic upgrade head` aus und danach pytest. Das Frontend installiert die Abhängigkeiten, prüft die Typen über den Lint-Lauf und baut das Bundle. Der Workflow enthält nur das Platzhalter-Passwort der Action-Datenbank. In dieser Sitzung wurde die Action auf GitHub nicht gestartet.

## Abgedeckte Bereiche

Die Suite prüft unter anderem:

- Health der API
- Partner, Kontakte, Aktivitäten und Aufgaben
- Deals, Produkte, Preise, Mehrwertsteuer und Bestellstatus
- Tickets, Anhänge, Segmente
- Kampagnen, Einwilligung, Automatisierungen und Benachrichtigungen
- Reporting, Export, Anmeldung, Passwort-Reset, CSRF und Rollen
- Mock-ERP: Verbindung, Vorschau ohne Schreiben, Import, Konflikte, Übertragung, Idempotenz, begrenzte Wiederholungen, Hintergrundlauf
- einen zusammenhängenden Ablauf von Partner bis Mock-Status, Abmelden und erneutem Anmelden

## Manuell

Für eine Vorführung: als Administrator anmelden, ERP-Integration auf Mock-ERP stellen, Verbindung testen, Katalogvorschau und Synchronisation ausführen, Ristorante Lago und die Bestellung DEMO-BP-1001 öffnen. Die Oberfläche muss das Mock-ERP als Testdaten kennzeichnen.

## Bekannte Einschränkungen

- Docker war auf dem Prüfgerät nicht installiert. Der Compose-Start ist nicht ausgeführt.
- GitHub Actions ist konfiguriert, in dieser Sitzung aber nicht auf GitHub gelaufen.
- Es gibt kein vorgelagertes Rate-Limiting ausser der Sperre je Benutzerkonto.
- `SESSION_COOKIE_SECURE` bleibt lokal falsch, weil der Browser das Cookie sonst über HTTP nicht sendet.
- Der Frontend-Build warnt, weil ein JavaScript-Bündel grösser als 500 Kilobyte ist.
- Externe ERP-Anbindung, automatische Bestellübertragung und ein Produktivbetrieb sind nicht umgesetzt.
- PDF-Berichte enthalten keine eingebetteten Diagramme. Der CSV-Export ist von den Tests abgedeckt.
