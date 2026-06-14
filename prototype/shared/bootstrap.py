"""
Globale Start-Hilfe für direkt ausgeführte Prototyp-Dateien.

Bei Starts über einen Dateipfad enthält sys.path nicht immer das Projektroot.
Dieses Modul stellt sicher, dass Importe wie ``prototype.shared``,
``apps.core`` und ``src.v5`` unabhängig vom Startort funktionieren.
"""

import sys
from pathlib import Path


def find_prototype_dir(start_file: str | Path) -> Path:
    """
    Sucht das Verzeichnis mit dem Namen "prototype", beginnend im Verzeichnis
    des angegebenen Startpfads. Die Suche steigt die Verzeichnisstruktur
    rekursiv nach oben, bis das Verzeichnis gefunden wird. Wenn kein solches
    Verzeichnis gefunden wird, wird eine Ausnahme ausgelöst.

    :param start_file: Der Pfad zu einer Datei oder einem Verzeichnis, in
        dessen Verzeichnisbaum nach einem Verzeichnis namens "prototype"
        gesucht werden soll.
    :type start_file: str | Path
    :return: Das gefundene Verzeichnis mit dem Namen "prototype".
    :rtype: Path
    :raises RuntimeError: Wenn kein Verzeichnis mit dem Namen "prototype"
        im Verzeichnisbaum gefunden wird.
    """
    current_path = Path(start_file).resolve()

    for parent in current_path.parents:
        if parent.name == "prototype":
            return parent

    raise RuntimeError(f"Prototype-Verzeichnis konnte nicht gefunden werden: {current_path}")


def ensure_project_import_paths(start_file: str | Path) -> tuple[Path, Path]:
    """
    Stellt sicher, dass die Importpfade für das Projekt korrekt konfiguriert sind, indem die
    übergeordneten Verzeichnisse des Prototyps und des Projektwurzelverzeichnisses
    hinzugefügt werden, falls sie noch nicht vorhanden sind.

    :param start_file: Der Pfad zur Startdatei, von dem aus der Suchprozess für das
        Prototyp-Verzeichnis beginnt.
    :return: Ein Tupel, das `prototype_dir` und `project_root` enthält. `prototype_dir` ist das
        Verzeichnis, in dem sich die prototypische Implementierung befindet. `project_root`
        ist das übergeordnete Verzeichnis des `prototype_dir`.
    """
    prototype_dir = find_prototype_dir(start_file)
    project_root = prototype_dir.parent

    for path in [project_root, prototype_dir]:
        path_value = str(path)

        if path_value not in sys.path:
            sys.path.insert(0, path_value)

    return prototype_dir, project_root
