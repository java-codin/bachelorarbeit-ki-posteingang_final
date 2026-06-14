"""Hilfsfunktionen für die kanonische Darstellung von E-Mail-Adressen.

Die Normalisierung wird von Worker- und Workflow-Code geteilt, damit Versand-
und Log-Metadaten dieselbe Adressform verwenden.
"""

from email.utils import parseaddr


def normalize_email_address(value: str | None) -> str | None:
    if not value:
        return None

    _, address = parseaddr(value)
    return (address or value).strip() or None
