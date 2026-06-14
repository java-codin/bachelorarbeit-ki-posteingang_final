# KI-Assistenzsystem für kommunale Bürgeranliegen

Dieses Repository enthält einen Python-Prototyp zur Verarbeitung kommunaler Bürgeranliegen. Der Prototyp kann Anliegen klassifizieren, zuständigen Stellen zuordnen, relevante Informationen aus einer Wissensbasis abrufen und bei geeigneter Quellenlage einen Antwortentwurf erzeugen.

## Funktionsweise

Der Prototyp verarbeitet ein Bürgeranliegen als Freitext und führt es je nach Version durch mehrere Verarbeitungsschritte:

1. **Eingabe analysieren**  
   Das Anliegen wird als Nutzereingabe übernommen und für die weitere Pipeline vorbereitet.

2. **Prompt-Injection prüfen**  
   Sicherheitsnahe Inhalte wie Aufforderungen zum Ignorieren von Systemregeln werden erkannt und als Bestandteil der Nutzereingabe behandelt.

3. **Anliegen klassifizieren**  
   Die Pipeline ordnet das Anliegen einer fachlichen Kategorie und möglichen Zielstellen zu.

4. **Routing bestimmen**  
   Es werden passende Fachbereiche, Teams oder Zieladressen vorgeschlagen. Die Ausgabe enthält je nach Version Top-1- oder Top-3-Vorschläge, Confidence-Werte und Begründungen.

5. **Wissensbasis durchsuchen**  
   Für Antwortentwürfe werden passende Inhalte aus der lokalen Wissensbasis abgerufen.

6. **Antwortentwurf erstellen**  
   Wenn geeignete Quellen vorhanden sind, wird ein quellengebundener Antwortentwurf erzeugt. Bei Unsicherheit wird stattdessen ein Fallback, eine Rückfrage oder eine Human-Review-Empfehlung ausgegeben.

7. **Risiko und Workflow-Status bestimmen**  
   Die Pipeline bewertet, ob der Fall automatisch vorbereitet werden kann oder eine menschliche Prüfung benötigt.

8. **Ergebnis anzeigen oder exportieren**  
   Die Ergebnisse können über Pipeline-Skripte, Streamlit-Oberflächen oder den statischen Report betrachtet werden.

## Projektstruktur

```text
prototype/
  apps/                       Streamlit-Anwendungen
  config/                     Konfigurationen für Kommune, Modelle und Policies
  data/
    inquiries/                Testanliegen
    knowledge_base/           Wissensbasis für Retrieval und Antwortentwürfe
  pipelines/                  Startpunkte für V0 bis V5
  reports/
    evaluation_site/          statischer Evaluationsreport
  scripts/                    Windows-Startskripte
  shared/                     gemeinsam genutzte Hilfsfunktionen
  src/
    core/                     versionsübergreifende Kernlogik
    v0/ ... v5/               Implementierungen der einzelnen Pipeline-Versionen
  tests/                      automatisierte und manuelle Tests
```

## Installation

Voraussetzungen:

- Python 3.12 oder neuer
- Windows PowerShell oder ein kompatibles Terminal
- optional: Docker für die E-Mail-Demo
- optional: OpenAI API-Key für OpenAI-basierte Modellprofile
- optional: lokale Modelle oder Ollama für lokale Modellprofile

Installation:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Die Datei `.env` enthält lokale Einstellungen wie API-Keys, Modellprofile oder Laufzeitoptionen. Sie muss vor der Nutzung bei Bedarf angepasst werden.

## Konfiguration

Die wichtigsten Konfigurationsdateien liegen hier:

```text
prototype/config/municipality.yaml
prototype/config/municipality_v2.yaml
prototype/config/model_profiles.yaml
.env.example
```

In den Municipality-Dateien werden fachliche Zuständigkeiten, Weiterleitungsziele und Policies gepflegt. In `model_profiles.yaml` werden die verfügbaren Modellprofile definiert.

## Pipeline direkt ausführen

Die aktuelle Hauptversion kann direkt über das Pipeline-Skript gestartet werden:

```powershell
.\.venv\Scripts\activate
python prototype\pipelines\run_v5.py
```

Weitere Versionen können analog gestartet werden:

```powershell
python prototype\pipelines\run_v0.py
python prototype\pipelines\run_v1.py
python prototype\pipelines\run_v2.py
python prototype\pipelines\run_v3.py
python prototype\pipelines\run_v4.py
```

## Streamlit-Anwendungen starten

Die wichtigsten Oberflächen können über die Skripte im Ordner `prototype/scripts/` gestartet werden.

Research-Webapp:

```powershell
.\prototype\scripts\start_research_webapp.bat
```

Webapp für den Prototyp:

```powershell
.\prototype\scripts\start_webapp.bat
```

Operations-Dashboard:

```powershell
.\prototype\scripts\start_operations_dashboard.bat
```

Team-Review:

```powershell
.\prototype\scripts\start_team_review.bat
```

Chunking-Experiment:

```powershell
.\prototype\scripts\start_chunking_experiment_app.bat
```

E-Mail-Demo:

```powershell
.\prototype\scripts\start_email_system.bat
```

## Typischer Ablauf

1. Virtuelle Umgebung aktivieren.
2. `.env` aus `.env.example` erstellen und bei Bedarf anpassen.
3. Gewünschtes Modellprofil auswählen.
4. Eine Pipeline oder Streamlit-App starten.
5. Bürgeranliegen eingeben oder Testdaten verwenden.
6. Klassifikation, Routing, Quellen, Antwortentwurf und Workflow-Status prüfen.

## Statischer Report

Der statische Report liegt unter:

```text
prototype/reports/evaluation_site/index.html
```

Die Datei kann direkt im Browser geöffnet oder über GitHub Pages veröffentlicht werden.

## Tests

Die automatisierten Tests können mit `pytest` ausgeführt werden:

```powershell
pytest
```

Manuelle Prüffälle liegen unter:

```text
prototype/tests/manual/
```