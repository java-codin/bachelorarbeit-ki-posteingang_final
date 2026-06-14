# Kommunale Wissensbasis v3 - Beispielkommune Musterstadt

Dieses Paket enthält eine fiktive, aber realistisch strukturierte kommunale Wissensbasis für den KI-Posteingangsprototyp.

## Inhalt

- 12 Fachteams
- 36 Fachdokumente
- 3 Dokumente pro Fachteam
- Jedes Dokument liegt als PDF und Markdown vor
- Dateinamen sind bewusst ohne Umlaute gehalten
- Dokumenttitel und Fließtexte verwenden normale deutsche Umlaute

## Struktur

```text
v3/
├─ abfall_bauhof/
├─ bauamt/
├─ buergerbuero/
├─ finanzen_steuern/
├─ gewerbeamt/
├─ jugend_familie/
├─ ordnungsamt/
├─ schule_bildung/
├─ soziales/
├─ stadtplanung/
├─ standesamt/
├─ umwelt_klima/
├─ document_overview.csv
├─ metadata.json
└─ README.md
```

## Verwendung im Prototyp

Empfohlener Ablageort:

```text
prototype/data/knowledge_base/v3/
```

Für RAG sollte vorzugsweise die Markdown-Version indexiert werden. Die PDF-Dateien dienen als realistischere Quellenbasis für Demo, Fachteam-Ansicht und Dokumentation.

## Hinweis

Alle Inhalte sind fiktiv. Sie stellen keine Rechtsauskunft dar und sind nicht für echte Verwaltungsverfahren geeignet.
