# Wissensbasis V5

Diese Wissensbasis ist für die organisationsstrukturierte V5-Pipeline erstellt worden. Sie orientiert sich an `prototype/config/municipality_v2.yaml` und verwendet die Ebenen:

1. Dezernat
2. Fachbereich
3. Bereich
4. Team

Die Dateiablage ist zweistufig nach Fachbereich und Bereich gegliedert. Die Retrieval-Kategorie steht zusätzlich explizit im Header jedes Dokuments, damit V5 nicht ausschließlich vom Ordnernamen abhängig ist.

## Strukturregeln

- `Fachbereich` ist das erste Routingziel der V5-Klassifikation.
- `Bereich` entspricht dem Feld `matched_subteam` aus Kompatibilitätsgründen.
- `Team` entspricht dem Feld `matched_team`.
- Die Begriffe `Fachteam` und `Subteam` werden in V5-Dokumenten bewusst vermieden.
- Formelle Anträge, Anzeigen oder Erklärungen werden nicht allein durch eine E-Mail ersetzt.
- Für formelle Vorgänge ist der vorgesehene Online-, Termin- oder Vorspracheweg zu nennen.

## Umfang

Erzeugte Markdown-Dokumente: 112

Diese Wissensbasis enthält ausschließlich fiktive Beispielinhalte für Prototyp- und Evaluationszwecke.

## Überarbeitungsstand: kommunenspezifisch angereicherte Version

Diese Ausgabe wurde für den kommunalen KI-Routing-Prototyp sprachlich überarbeitet und um kommunenspezifische Informationen der fiktiven Stadt Musterstadt ergänzt. Die Ergänzungen betreffen insbesondere:

- zentraler Eingangskanal `buergeranliegen@kommune.test`,
- fiktiver Verwaltungssitz Marktplatz 1, 12345 Musterstadt,
- Serviceportal und Terminlogik der Stadt Musterstadt,
- örtliche Anlaufstellen je Fachbereich,
- interne Weiterleitung als Arbeitspaket an Fachteams,
- fachliche Freigabe vor Versand an Bürgerinnen und Bürger,
- Plausibilitätsprüfung bei widersprüchlichem Routing und Retrieval,
- Hinweise für Antwortvollständigkeit, Quellenbindung und Datenschutz.

Die Dateien enthalten weiterhin keine Echtdaten. Dateinamen und technische IDs bleiben ASCII-kompatibel; die Dokumenttexte verwenden normale deutsche Umlaute.

**Überarbeitete Markdown-Dateien:** 112  
**Erstellt am:** 2026-06-11T19:28:17
