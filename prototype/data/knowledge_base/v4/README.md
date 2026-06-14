# Kommunale Wissensbasis V4 - Beispielkommune Musterstadt

Diese Wissensbasis ist eine fiktive, kommunenspezifischere Erweiterung der V3-Wissensbasis für den KI-Posteingangsprototyp.

## Inhalt

- 12 Fachbereiche bzw. Fachteams
- 108 fachliche Markdown-Dokumente
- 9 Dokumente pro Fachteam
- eindeutige Zuordnung jedes Dokuments zu einem Subteam aus `prototype/config/municipality_v2.yaml`
- ausschließlich Markdown-Dateien, keine PDF-, CSV- oder JSON-Dateien
- fiktive Beispielkommune, keine Echtdaten, keine personenbezogenen Realinformationen

## Ziel

V4 soll die Antwortgenerierung verbessern, indem mehr konkrete kommunale Abläufe, benötigte Angaben, Abgrenzungen und Antwort-Hinweise bereitstehen. Die Dokumente sind nicht als Rechtsauskunft zu verstehen, sondern als Design-Science-Testdaten für Routing, Retrieval, Antwortentwurf und Human-in-the-Loop-Freigabe.

## Nutzungshinweis

Für RAG und Evaluation sollten nur die Markdown-Dateien indexiert werden. Die Antwortentwürfe sollen weiterhin vorsichtig formuliert werden und keine verbindlichen Verwaltungsentscheidungen ohne fachliche Prüfung treffen.

## Fachteam- und Subteam-Struktur

Jedes Service-Dokument enthält im Header neben dem zuständigen Fachteam auch die Felder `Zuständiges Subteam`, `Subteam-ID` und `Subteam-Beschreibung`. Die Subteam-Zuordnung orientiert sich an der V5-Konfiguration `municipality_v2.yaml`. Dadurch kann die V5-Pipeline weiterhin auf Fachbereichsebene routen, zugleich aber für Signatur, Antwortrolle, Retrieval-Kontext und Evaluation das fachlich passende Subteam mitführen.

Die `Such- und Routingbegriffe` enthalten zusätzlich den Subteam-Namen, die Subteam-ID sowie die wichtigsten subteambezogenen Leistungen und Keywords. Das soll insbesondere Fälle verbessern, in denen mehrere Leistungen innerhalb eines Fachbereichs nah beieinanderliegen.

## Service-Klassifikation und Antragstellung

Jedes fachliche Dokument enthält eine explizite Service-Einordnung mit den Metadaten `Service-Art`, `Antrags-/Portalhinweis` und `Geltung Antragstellungsregel`. Dadurch soll im Retrieval klarer werden, ob eine E-Mail selbst ausreicht, ob sie nur eine Vorbereitung ist oder ob ein formeller Antrag über einen offiziellen Kanal erforderlich bleibt.

Die Antragstellungs- und Portalregel gilt unmittelbar für Antragsleistungen und formelle Anzeigen oder Erklärungen, zum Beispiel Ausweisdokumente, Urkunden, Gewerbevorgänge, Bauanträge, Wohngeld, Wohnberechtigungsschein oder Sondernutzungen. In diesen Fällen soll der Antwortentwurf deutlich machen, dass der eigentliche Vorgang persönlich im zuständigen Amt oder über das Online-Portal der Stadt, des Kreises, des Landes oder des Bundes zu stellen ist.

Bei Meldungen, Beschwerden und Mängelhinweisen gilt die Regel nicht als Antragspflicht. Dort kann die E-Mail aufgenommen werden; falls ein städtischer Mängelmelder, ein Online-Formular oder eine Fachplattform vorgesehen ist, soll der Entwurf darauf verweisen.

Bei Auskunfts-, Beratungs-, Beteiligungs-, Planungs-, Abgaben- oder Bescheidfällen gilt die Regel abhängig vom konkreten Folgevorgang. Allgemeine Rückfragen können per E-Mail beantwortet werden, während formelle Stellungnahmen, Rechtsbehelfe, Mandate, Anträge oder verbindliche Erklärungen über den vorgesehenen schriftlichen, persönlichen oder digitalen Kanal laufen müssen.
