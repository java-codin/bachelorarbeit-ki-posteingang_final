import unittest

from src.v5.answer import strip_inline_source_markers
from src.v5.api.v5_api import select_answer_chunks_for_target_team
from src.v5.source_extraction import attach_source_ids, resolve_used_sources
from src.v5.core.constants import (
    K_CATEGORY,
    K_CHUNK_ID,
    K_CONTENT,
    K_INVALID_SOURCE_IDS,
    K_SOURCE,
    K_SOURCE_ID,
    K_USED_CHUNKS,
    K_USED_SOURCE_IDS,
    K_USED_SOURCES,
)


class V5SourcePresentationTests(unittest.TestCase):
    def test_inline_source_markers_are_removed_from_citizen_answer(self):
        answer = (
            "Guten Tag,\n\n"
            "Sie können den Reisepass im Buergerbuero beantragen. [S1]\n"
            "Bitte bringen Sie die erforderlichen Unterlagen mit. [S2]"
        )

        result = strip_inline_source_markers(answer)

        self.assertNotIn("[S1]", result)
        self.assertNotIn("[S2]", result)
        self.assertIn("Reisepass", result)

    def test_nested_llm_answer_object_is_converted_to_text(self):
        answer = {
            "draft_answer": (
                "Guten Tag,\n\n"
                "Der Antrag wird vom Bürgerbüro bearbeitet. [S1]"
            )
        }

        result = strip_inline_source_markers(answer)

        self.assertNotIn("[S1]", result)
        self.assertIn("Buergerbuero", result)

    def test_source_ids_still_resolve_for_internal_traceability(self):
        chunks = attach_source_ids([
            {
                K_SOURCE: "BB-01_Reisepass_Beantragung.md",
                K_CHUNK_ID: "bb-01::1",
                K_CONTENT: "Reisepass beantragen",
            },
            {
                K_SOURCE: "BB-02_Personalausweis_Beantragung.md",
                K_CHUNK_ID: "bb-02::1",
                K_CONTENT: "Personalausweis beantragen",
            },
        ])

        result = resolve_used_sources(["S1"], chunks)

        self.assertEqual(result[K_USED_SOURCE_IDS], ["S1"])
        self.assertEqual(result[K_USED_SOURCES], ["BB-01_Reisepass_Beantragung.md"])
        self.assertEqual(result[K_USED_CHUNKS][0][K_SOURCE_ID], "S1")
        self.assertEqual(result[K_INVALID_SOURCE_IDS], [])

    def test_answer_context_prefers_chunks_from_target_team(self):
        chunks = [
            {K_CATEGORY: "buergerbuero", K_SOURCE: "BB-02_Personalausweis_Beantragung.md"},
            {K_CATEGORY: "soziales", K_SOURCE: "SO-02_Grundsicherung_Sozialhilfe.md"},
            {K_CATEGORY: "soziales", K_SOURCE: "SO-01_Wohngeld_Beantragen.md"},
        ]

        selected = select_answer_chunks_for_target_team(chunks, "buergerbuero")

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0][K_SOURCE], "BB-02_Personalausweis_Beantragung.md")

    def test_answer_context_is_empty_when_target_team_is_missing(self):
        chunks = [
            {K_CATEGORY: "buergerbuero", K_SOURCE: "BB-03_Wohnsitz_Anmeldung_Ummeldung.md"},
            {K_CATEGORY: "gewerbeamt", K_SOURCE: "GA-01_Gewerbeanmeldung.md"},
        ]

        selected = select_answer_chunks_for_target_team(chunks, "standesamt")

        self.assertEqual(selected, [])


if __name__ == "__main__":
    unittest.main()
