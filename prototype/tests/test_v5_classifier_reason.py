import unittest
from unittest.mock import patch

from src.v5.classifier import (
    classify,
    normalize_classification_reason,
)
from src.v5.core.prompt_templates import CLASSIFIER_SYSTEM_PROMPT
from src.v5.core.constants import (
    K_CONFIDENCE,
    K_DESCRIPTION,
    K_DIVISIONS,
    K_EMAIL,
    K_KEYWORDS,
    K_MATCHED_SUBTEAM,
    K_MATCHED_TEAM,
    K_NAME,
    K_REASON,
    K_SERVICES,
    K_TEAMS,
    K_TOP3,
    K_TOP_TEAM,
    V_UNKNOWN,
)


CLASSIFIER_CONFIG = {
    K_TEAMS: {
        "buergerbuero": {
            K_NAME: "Buergerbuero",
            K_DESCRIPTION: "Ausweisdokumente und allgemeine Bürgerdienste.",
            K_KEYWORDS: ["reisepass", "personalausweis"],
            K_SERVICES: ["Reisepass beantragen", "Personalausweis beantragen"],
            K_EMAIL: "buergerbuero@example.test",
        },
        "standesamt": {
            K_NAME: "Standesamt",
            K_DESCRIPTION: "Personenstandsfälle und Urkunden.",
            K_KEYWORDS: ["geburtsurkunde", "eheschliessung"],
            K_SERVICES: ["Geburtsurkunde beantragen", "Eheschliessung anmelden"],
            K_EMAIL: "standesamt@example.test",
        },
        "ordnungsamt": {
            K_NAME: "Ordnungsamt",
            K_DESCRIPTION: "Sicherheit und Ordnung.",
            K_KEYWORDS: ["falschparker", "ruhestoerung"],
            K_SERVICES: ["Falschparker melden", "Ruhestörung melden"],
            K_EMAIL: "ordnungsamt@example.test",
        },
    }
}


class V5ClassifierReasonTests(unittest.TestCase):
    def test_technical_keyword_reason_is_replaced_with_fachliche_reason(self):
        result = normalize_classification_reason(
            "Das Anliegen passt zu den Keywords 'reisepass' und 'beantragen', "
            "die dem Team 'buergerbuero' zugeordnet sind.",
            "buergerbuero",
            {"buergerbuero": "Buergerbuero"},
        )

        self.assertNotIn("Keyword", result)
        self.assertNotIn("buergerbuero", result)
        self.assertIn("Buergerbuero", result)
        self.assertIn("fachlich", result)

    def test_unknown_team_gets_uncertainty_reason(self):
        result = normalize_classification_reason(
            "Die YAML-Zustaendigkeitsmatrix lässt keine eindeutige Zuordnung zu.",
            V_UNKNOWN,
            {"buergerbuero": "Buergerbuero"},
        )

        self.assertIn("nicht eindeutig", result)
        self.assertNotIn("YAML", result)

    def test_non_technical_reason_is_kept_but_team_id_is_replaced(self):
        result = normalize_classification_reason(
            "Das Anliegen betrifft die Beantragung eines Reisedokuments und passt "
            "deshalb zum Aufgabenbereich von buergerbuero.",
            "buergerbuero",
            {"buergerbuero": "Buergerbuero"},
        )

        self.assertEqual(
            result,
            "Das Anliegen betrifft die Beantragung eines Reisedokuments und passt "
            "deshalb zum Aufgabenbereich von Buergerbuero.",
        )

    @patch("src.v5.classifier.chat_json")
    def test_classification_corrects_llm_decision_with_clear_config_service_match(self, mock_chat_json):
        mock_chat_json.return_value = {
            K_TOP_TEAM: "standesamt",
            K_TOP3: ["standesamt", "ordnungsamt"],
            K_CONFIDENCE: 1.0,
            K_REASON: (
                "Der Bürger möchte einen Reisepass beantragen, was in den "
                "Aufgabenbereich des Standesamts fällt."
            ),
        }

        result = classify(
            "Ich möchte einen neuen Reisepass beantragen. Welche Unterlagen benötige ich?",
            CLASSIFIER_CONFIG,
        )

        self.assertEqual(result[K_TOP_TEAM], "buergerbuero")
        self.assertEqual(result[K_TOP3][0], "buergerbuero")
        self.assertLess(result[K_CONFIDENCE], 1.0)
        self.assertIn("Buergerbuero", result[K_REASON])

    @patch("src.v5.classifier.chat_json")
    def test_email_like_request_can_be_corrected_by_clear_service_match(self, mock_chat_json):
        mock_chat_json.return_value = {
            K_TOP_TEAM: "standesamt",
            K_TOP3: ["standesamt"],
            K_CONFIDENCE: 0.9,
            K_REASON: "Formale Mail, daher Standesamt.",
        }

        email_text = (
            "Sehr geehrte Damen und Herren,\n\n"
            "ich möchte einen Reisepass beantragen und bitte um Informationen "
            "zu den benötigten Unterlagen.\n\n"
            "Mit freundlichen Grußessen\nMax Mustermann"
        )

        result = classify(email_text, CLASSIFIER_CONFIG)

        self.assertEqual(result[K_TOP_TEAM], "buergerbuero")
        self.assertEqual(result[K_TOP3][0], "buergerbuero")
        self.assertLess(result[K_CONFIDENCE], 0.9)

    @patch("src.v5.classifier.chat_json")
    def test_corrected_department_allows_division_and_team_inference(self, mock_chat_json):
        mock_chat_json.return_value = {
            K_TOP_TEAM: "registry_office",
            K_TOP3: ["registry_office"],
            K_CONFIDENCE: 1.0,
            K_REASON: "Reisepass sei Standesamt.",
        }
        config = {
            K_TEAMS: {
                "citizen_services": {
                    K_NAME: "Bürgerdienste",
                    K_KEYWORDS: ["reisepass"],
                    K_SERVICES: ["Reisepass beantragen"],
                    K_DIVISIONS: {
                        "citizens_office": {
                            K_NAME: "Buergerbuero",
                            K_KEYWORDS: ["reisepass"],
                            K_SERVICES: ["Reisepass beantragen"],
                            K_TEAMS: {
                                "id_cards_travel_documents": {
                                    K_NAME: "Ausweise und Reisedokumente",
                                    K_KEYWORDS: ["reisepass"],
                                    K_SERVICES: ["Reisepass beantragen"],
                                }
                            },
                        }
                    },
                },
                "registry_office": {
                    K_NAME: "Standesamt",
                    K_KEYWORDS: ["geburtsurkunde"],
                    K_SERVICES: ["Geburtsurkunde beantragen"],
                },
            }
        }

        result = classify(
            "Ich möchte einen Reisepass beantragen.",
            config,
        )

        self.assertEqual(result[K_TOP_TEAM], "citizen_services")
        self.assertEqual(result[K_MATCHED_SUBTEAM], "citizens_office")
        self.assertEqual(result[K_MATCHED_TEAM], "id_cards_travel_documents")

    def test_classifier_prompt_requires_email_frame_and_consistency_check(self):
        self.assertIn("Ignoriere E-Mail-Rahmen", CLASSIFIER_SYSTEM_PROMPT)
        self.assertIn("fachliche Hauptanliegen", CLASSIFIER_SYSTEM_PROMPT)
        self.assertIn("Die Begründung muss zwingend zum ausgegebenen top_team passen", CLASSIFIER_SYSTEM_PROMPT)
        self.assertIn("top3 muss mit top_team beginnen", CLASSIFIER_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
