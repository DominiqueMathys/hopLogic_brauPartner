# Benutzung

Die Oberfläche spricht Deutsch und verwendet die Schweizer Schreibweise. Datum und Zeit folgen der Zone Europe/Zurich. Geldbeträge erscheinen in CHF.

Alle mitgelieferten Firmen, Personen und Belege sind fiktiv. Sie beschreiben keine echte Kundenbeziehung des Liechtensteiner Brauhauses.

## Anmeldung

Die Anmeldung verlangt eine geschäftliche E-Mail und ein Passwort. Nach fünf fehlgeschlagenen Versuchen sperrt das Konto vorübergehend. Abmelden beendet die Sitzung. Ein Passwort-Reset sendet in der lokalen Entwicklung keinen echten Brief. Der Token wird nur als Hash gespeichert.

Die Navigation zeigt nur Menüpunkte, für die die Rolle ein Leserecht hat. Ein direkter API-Aufruf ohne Recht antwortet mit 401 oder 403.

## Vertriebspartner

Partner lassen sich erstellen, suchen, filtern, bearbeiten, archivieren und wiederherstellen. Auf der Detailseite stehen ERP-Kundennummer, ERP-Kundenstatus, Quelle und der Zeitpunkt der letzten ERP-Aktualisierung. «Mock-ERP, Testdaten» bedeutet eine Testquelle, keine echte ERP-Verbindung.

Das Beispiel Ristorante Lago in Locarno trägt die fiktive Kundennummer 10457. Die Kontaktperson ist Giulia Bernasconi.

## Kontakte, Aktivitäten und Aufgaben

Kontakte werden einem oder mehreren Unternehmen zugeordnet. Eine primäre Firma ist je Kontakt eindeutig.

Aktivitäten dokumentieren Gespräche und Notizen. Aufgaben haben eine zuständige Person, eine Fälligkeit und einen Status. Erledigte Aufgaben bleiben nachvollziehbar.

## Verkaufschancen

Die Pipeline zeigt offene Phasen. Ein Deal lässt sich in eine andere offene Phase verschieben. Gewinnen und Verlieren schliessen den Deal. Die Historie speichert die Phasenwechsel. Das Beispiel heisst «Erweiterung des Biersortiments».

## Produkte und Bestellungen

Der Katalog führt Artikelnummer, Preis, Währung, Mehrwertsteuer und, nach einer Synchronisation, die ERP-Quelle. Eine Bestellung rechnet Menge, Rabatt und Steuer. Die Position speichert den Preis zum Bestellzeitpunkt.

Der Bestellstatus im CRM ist eine interne Angabe. Der Übertragungsstatus sagt nur, ob der Beleg an den konfigurierten Connector übergeben wurde. Die fiktive Bestellung DEMO-BP-1001 enthält mehrere Bierpositionen.

## Service-Tickets

Tickets dokumentieren Reklamationen, interne Notizen, Statuswechsel und die Historie. Anhänge sind auf PDF, JPG und PNG mit passendem Dateiinhalt und auf fünf Megabyte begrenzt. Sie liegen unter `data/ticket-attachments` und werden nicht öffentlich ausgeliefert. Das Beispiel beschreibt eine beschädigte Bierlieferung.

## Marketing und Automatisierungen

Kampagnen haben Zielgruppe, Kanal und Budget. Ein Kontakt ohne dokumentierte Einwilligung wird bei einem E-Mail-Kanal nicht als zustellbar behandelt. Die Kampagne «Winter-Sortiment 2026» ist ein fiktives Beispiel.

Eine aktive Automatisierung kann beim Anlegen eines Deals eine Aufgabe erzeugen. Die Aufgabe erscheint bei den Aufgaben des Partners. Benachrichtigungen lassen sich in der Kopfzeile öffnen. Die lokale Regel «Erstkontakt vorbereiten» ist ein Demo-Datensatz und soll nicht unbedacht deaktiviert werden.

## Reporting

Berichte lassen sich nach Zeitraum und Ausschnitt filtern. Exportiert wird nur, wer das Exportrecht hat. Ein Export ohne Recht wird abgelehnt und protokolliert, ohne den Bericht auszuliefern.

## ERP-Testintegration

Unter «ERP-Integration» wählt eine berechtigte Person den Modus Mock-ERP und testet die Verbindung. Die Vorschau verändert keine CRM-Daten. Erst «Synchronisation starten» schreibt Katalog oder Kundenstamm.

Eine Bestellung wird zuerst freigegeben und danach an das Mock-ERP übertragen. Die zurückgegebene Referenz beginnt mit `MOCK-AUF-`. «Externen Status abrufen» liest den simulierten Status. Der CRM-Status bleibt unverändert.

«Externes ERP» ist gesperrt, solange kein echter Connector und keine HTTPS-Konfiguration vorhanden sind.
