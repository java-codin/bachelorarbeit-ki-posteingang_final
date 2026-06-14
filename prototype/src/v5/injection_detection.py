"""LLM-gestützte Prompt-Injection-Erkennung der Pipeline v5.

Das Modul kombiniert regelbasierte Vorprüfung mit einem JSON-basierten Judge,
damit manipulative Nutzerinhalte nicht als Systemanweisung behandelt werden.
"""

import re

from prototype.shared.logging_config import get_logger
from prototype.shared.model_profiles import LLM_STEP_INJECTION_DETECTION
from src.core.llm_client import chat_json, current_llm_step_model
from src.v5.core.constants import (
    K_CONFIDENCE,
    K_CONTENT_MSG,
    K_DETECTED,
    K_MATCHED_PATTERNS,
    K_REASONING,
    K_ROLE,
    ROLE_SYSTEM,
    ROLE_USER,
)
from src.v5.core.prompt_templates import (
    INJECTION_DETECTION_SYSTEM_PROMPT,
    INJECTION_DETECTION_USER_PROMPT,
)
from src.v5.core.response_messages import INJECTION_ERROR_REASON, LOG_INJECTION_ERROR


logger = get_logger(__name__)


STATIC_INJECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "ignore_previous_instructions",
        r"\b(ignore|disregard|forget|override)\b.{0,80}"
        r"\b(previous|prior|above|all)\b.{0,80}\b(instructions|rules|prompts?)\b",
    ),
    (
        "ignore_rules_de",
        r"\b(ignoriere|vergiss|ueberschreibe|überschreibe)\b.{0,80}"
        r"\b(vorherige|bisherige|alle|obige)\b.{0,80}\b(anweisungen|regeln|prompts?)\b",
    ),
    (
        "system_prompt_extraction",
        r"\b(system[- ]?prompt|developer message|hidden instructions?|"
        r"interne anweisungen|systemanweisung(en)?)\b",
    ),
    (
        "prompt_leak_request",
        r"\b(show|print|reveal|expose|leak|dump|zeige|drucke|gib)\b.{0,80}"
        r"\b(prompt|system prompt|instructions?|anweisungen|regeln)\b",
    ),
    (
        "role_override",
        r"\b(du bist jetzt|you are now|act as|pretend to be|rolle eines|roleplay)\b",
    ),
    (
        "jailbreak_marker",
        r"\b(jailbreak|dan mode|developer mode|bypass|"
        r"sicherheitsfilter umgehen|filter umgehen)\b",
    ),
    (
        "tool_or_command_injection",
        r"\b(cmd|powershell|bash|shell|terminal)\b.{0,80}"
        r"\b(ausfuehren|ausführen|execute|run|starte|start)\b",
    ),
)


def _find_static_matches(text: str) -> list[str]:
    """
    Erkennt offensichtliche Prompt-Injection-Muster ohne LLM-Aufruf.
    """
    return [
        name
        for name, pattern in STATIC_INJECTION_PATTERNS
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    ]


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "ja"}
    return False


def _as_confidence(value: object, default: float = 0.0) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, confidence))


def detect_prompt_injection(text: str) -> dict:
    """
    Analysiert den eingegebenen Text auf Prompt-Injection-Versuche.

    Die Erkennung kombiniert eine deterministische Vorprüfung für offensichtliche
    Angriffe mit einem LLM-basierten semantischen Judge. Dadurch bleibt v5
    auditierbar und reduziert zugleich das Risiko, dass der Judge selbst durch
    den zu prüfenden Text manipuliert wird.
    """
    static_matches = _find_static_matches(text)
    if static_matches:
        return {
            K_DETECTED: True,
            K_REASONING: (
                "Deterministische Sicherheitsregel erkannt: "
                + ", ".join(static_matches)
            ),
            K_CONFIDENCE: 1.0,
            K_MATCHED_PATTERNS: static_matches,
        }

    user_prompt = INJECTION_DETECTION_USER_PROMPT.format(text=text)
    messages = [
        {K_ROLE: ROLE_SYSTEM, K_CONTENT_MSG: INJECTION_DETECTION_SYSTEM_PROMPT},
        {K_ROLE: ROLE_USER, K_CONTENT_MSG: user_prompt},
    ]

    try:
        provider, model, temperature = current_llm_step_model(LLM_STEP_INJECTION_DETECTION)
        response = chat_json(messages, provider=provider, model=model, temperature=temperature)
        detected = _as_bool(response.get(K_DETECTED, False))
        confidence = _as_confidence(response.get(K_CONFIDENCE, 0.0))

        return {
            K_DETECTED: detected,
            K_REASONING: response.get(K_REASONING, ""),
            K_CONFIDENCE: confidence,
            K_MATCHED_PATTERNS: ["llm_semantic_detection"] if detected else [],
        }
    except Exception as exc:
        # Fail-closed: Bei Ausfall des LLM-Judges wird der Fall nicht automatisch verarbeitet.
        logger.exception(LOG_INJECTION_ERROR.format(exc=exc))
        return {
            K_DETECTED: True,
            K_REASONING: INJECTION_ERROR_REASON,
            K_CONFIDENCE: 0.5,
            K_MATCHED_PATTERNS: ["llm_detection_error_fail_closed"],
        }
