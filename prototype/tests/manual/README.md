# Manuelle Hilfsskripte

Dieser Ordner ist für lokale Smoke-Tests, Demo-Daten und Setup-Helfer vorgesehen.
Er wird durch `pytest.ini` bewusst nicht von pytest gesammelt.

Skripte in diesem Ordner können lokale Dienste, Modelle oder API-Schlüssel
benötigen und sollten deshalb nicht Teil der automatischen Regressionstests sein.
