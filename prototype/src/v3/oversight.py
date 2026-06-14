"""Human-Oversight-Ableitung der Pipeline v3.

Das Modul bündelt Signale aus Klassifikation, Injection-Erkennung, Guardrails
und No-Answer-Logik zu einer manuellen Prüfentscheidung.
"""

from typing import Any
from src.v3.core import constants as c


def require_human_review(
        classification: dict[str, Any],
        injection_result: dict[str, Any],
        guardrail_result: dict[str, Any],
        no_answer_triggered: bool
) -> dict[str, Any]:
    """
    Prüft, ob menschliche Überprüfung erforderlich ist, basierend auf den übergebenen Ergebnissen und Metadaten.

    Die Funktion analysiert mehrere Eingabedaten, darunter Klassifikationsergebnisse, das Ergebnis
    einer Angriffserkennung (Prompt Injection), Ergebnisse von Guardrail-Überprüfungen sowie
    ein Flag, ob keine Antwort generiert wurde. Basierend auf diesen Informationen werden mögliche
    Gründe gesammelt und eine Entscheidung getroffen, ob eine menschliche Überprüfung
    erforderlich ist.

    :param classification: Ein Wörterbuch, das Ergebnisse und Metadaten der Klassifikation enthält.
        Erwartete Schlüssel sind unter anderem `c.K_TOP_TEAM`, `c.V_UNKNOWN` sowie
        `c.K_CONFIDENCE`. Der Wert von `c.K_CONFIDENCE` sollte eine numerische Konfidenz
        darstellen.
    :param injection_result: Ein Wörterbuch, das die Ergebnisse einer Überprüfung auf
        Prompt Injection enthält. Erwartete Schlüssel sind unter anderem `c.K_DETECTED`.
    :param guardrail_result: Ein Wörterbuch, das die Ergebnisse von Guardrail-Überprüfungen
        enthält. Erwartete Schlüssel beinhalten `c.K_FLAGS`.
    :param no_answer_triggered: Ein boolescher Wert, der angibt, ob ein Zustand ohne generierte
        Antwort vorlag.
    :return: Ein Wörterbuch mit zwei Schlüsseln:
        - `c.K_REQUIRED`: `bool`, gibt an, ob eine menschliche Überprüfung erforderlich ist.
        - `c.K_REASONS`: `list[str]`, eine Liste der gesammelten Gründe für die
          Überprüfung.
    """
    reasons = []

    if classification[c.K_TOP_TEAM] == c.V_UNKNOWN:
        reasons.append(c.REASON_UNKNOWN_TEAM)

    if classification[c.K_CONFIDENCE] < c.CLASSIFICATION_REVIEW_THRESHOLD:
        reasons.append(c.REASON_LOW_CONFIDENCE)

    if injection_result[c.K_DETECTED]:
        reasons.append(c.REASON_PROMPT_INJECTION)

    if no_answer_triggered:
        reasons.append(c.REASON_NO_ANSWER_TRIGGERED)

    if guardrail_result[c.K_FLAGS]:
        reasons.append(c.REASON_GUARDRAIL_FLAGS)

    return {
        c.K_REQUIRED: len(reasons) > 0,
        c.K_REASONS: reasons,
    }
