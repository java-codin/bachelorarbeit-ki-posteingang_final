import unittest
from unittest.mock import patch

from apps.core.mail.email_sender import send_smtp_mail
from apps.core.mail import email_worker_mailpit
from apps.core.workflow_actions import (
    build_citizen_reply_update,
    build_internal_forward_update,
)
from src.v5.core.prompt_templates import CLASSIFIER_USER_PROMPT


class EmailWorkerBodyInputTests(unittest.TestCase):
    def test_classifier_prompt_ignores_email_fluff_without_structured_subject(self):
        self.assertIn("Falls der Text aus einer E-Mail stammt", CLASSIFIER_USER_PROMPT)
        self.assertIn("Nachrichtentext", CLASSIFIER_USER_PROMPT)
        self.assertIn("Ignoriere Grußformeln", CLASSIFIER_USER_PROMPT)
        self.assertNotIn("Kernanliegen", CLASSIFIER_USER_PROMPT)

    @patch("apps.core.mail.email_worker_mailpit.mark_message_processed")
    @patch("apps.core.mail.email_worker_mailpit.update_worker_status")
    @patch("apps.core.mail.email_worker_mailpit.update_case")
    @patch("apps.core.mail.email_worker_mailpit.send_status_mail_to_citizen")
    @patch("apps.core.mail.email_worker_mailpit.create_case")
    @patch("apps.core.mail.email_worker_mailpit.run_version")
    @patch("apps.core.mail.email_worker_mailpit.normalize_mailpit_message")
    def test_worker_passes_only_body_to_pipeline(
            self,
            mock_normalize_message,
            mock_run_version,
            mock_create_case,
            mock_send_status_mail,
            _mock_update_case,
            _mock_update_worker_status,
            _mock_mark_message_processed,
    ):
        mock_normalize_message.return_value = {
            "to_inbox": True,
            "subject": "Wichtiger Betreff",
            "sender": "Max Mustermann <max@example.test>",
            "recipients": ["inbox@example.test"],
            "body": "Guten Tag,\n\nich habe ein Anliegen.\n\nMit freundlichen Grußessen\nMax",
        }
        mock_run_version.return_value = {
            "status": "ok",
            "response_mode": "normal",
            "target_team": "unknown",
            "target_email": None,
            "human_review_reasons": [],
        }
        mock_create_case.return_value = {
            "case_id": "case-1",
            "status": "needs_manual_routing",
        }
        mock_send_status_mail.return_value = {
            "sent": False,
            "status": "mocked",
            "to": "max@example.test",
        }

        processed = email_worker_mailpit.process_message_summary({"ID": "mail-1"})

        self.assertTrue(processed)
        mock_run_version.assert_called_once()
        _, inquiry_text = mock_run_version.call_args.args
        self.assertEqual(
            inquiry_text,
            "Guten Tag,\n\nich habe ein Anliegen.\n\nMit freundlichen Grußessen\nMax",
        )
        self.assertNotIn("Betreff:", inquiry_text)

        case_payload = mock_create_case.call_args.args[0]
        email_metadata = case_payload["email_metadata"]
        self.assertEqual(email_metadata["sender"], "Max Mustermann")
        self.assertEqual(email_metadata["from"], "max@example.test")
        self.assertEqual(email_metadata["sender_address"], "max@example.test")

    @patch("apps.core.mail.email_sender.smtplib.SMTP")
    def test_send_smtp_mail_stores_plain_from_address(self, mock_smtp):
        smtp_context = mock_smtp.return_value.__enter__.return_value

        result = send_smtp_mail(
            from_name="KI-Posteingang Musterstadt",
            from_email="buergeranliegen@kommune.test",
            to_email="max@example.test",
            subject="Test",
            body="Test",
            reply_to="buergeranliegen@kommune.test",
        )

        self.assertTrue(result["sent"])
        self.assertEqual(result["from"], "buergeranliegen@kommune.test")
        self.assertEqual(result["to"], "max@example.test")
        smtp_context.send_message.assert_called_once()
        sent_message = smtp_context.send_message.call_args.args[0]
        self.assertEqual(
            sent_message["From"],
            "KI-Posteingang Musterstadt <buergeranliegen@kommune.test>",
        )

    def test_workflow_updates_store_plain_address_fields(self):
        status_update = email_worker_mailpit.status_mail_update({
            "sent": True,
            "from": "KI-Posteingang Musterstadt <buergeranliegen@kommune.test>",
            "to": "Max Mustermann <max@example.test>",
            "subject": "Status",
            "sent_at": "2026-06-09T17:59:00",
            "status": "sent",
            "error": None,
        })
        self.assertEqual(
            status_update["status_mail"]["from"],
            "buergeranliegen@kommune.test",
        )
        self.assertEqual(status_update["status_mail"]["to"], "max@example.test")

        forward_update = build_internal_forward_update({
            "sent": True,
            "from": "KI-Posteingang Musterstadt <buergeranliegen@kommune.test>",
            "to": "Buergerbuero <buergerbuero@kommune.test>",
            "subject": "Weiterleitung",
            "body": "Text",
            "sent_at": "2026-06-09T18:00:00",
            "status": "sent",
            "error": None,
        })
        self.assertEqual(
            forward_update["internal_forward"]["from"],
            "buergeranliegen@kommune.test",
        )
        self.assertEqual(
            forward_update["internal_forward"]["to"],
            "buergerbuero@kommune.test",
        )

        citizen_reply = build_citizen_reply_update(
            case={"citizen_reply": {}},
            reply_result={
                "sent": True,
                "from": "Buergerbuero <buergerbuero@kommune.test>",
                "to": "Max Mustermann <max@example.test>",
                "subject": "Antwort",
                "sent_at": "2026-06-09T18:01:00",
                "status": "sent",
                "error": None,
            },
            final_answer="Antworttext",
        )
        self.assertEqual(citizen_reply["from"], "buergerbuero@kommune.test")
        self.assertEqual(citizen_reply["to"], "max@example.test")

    def test_valid_target_team_goes_to_team_review_even_with_incomplete_answer(self):
        result = {
            "status": "ok",
            "response_mode": "review_required",
            "target_team": "buergerbuero",
            "target_email": "buergerbuero@kommune.test",
            "confidence": 1.0,
            "human_review_reasons": ["incomplete_answer"],
        }

        self.assertEqual(
            email_worker_mailpit.determine_case_status(result),
            email_worker_mailpit.CASE_STATUS_TEAM_REVIEW_PENDING,
        )

    def test_unknown_target_team_stays_in_manual_routing(self):
        result = {
            "status": "ok",
            "response_mode": "review_required",
            "target_team": "unknown",
            "target_email": None,
            "confidence": 0.5,
            "human_review_reasons": ["unknown_team"],
        }

        self.assertEqual(
            email_worker_mailpit.determine_case_status(result),
            email_worker_mailpit.CASE_STATUS_NEEDS_MANUAL_ROUTING,
        )


if __name__ == "__main__":
    unittest.main()
