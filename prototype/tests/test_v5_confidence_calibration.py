import unittest

from src.v5.confidence_calibration import calibrate_confidence
from src.v5.core.constants import (
    K_COMPLETENESS_SCORE,
    K_ISSUES,
    K_PASSED,
    MODE_BLOCKED,
    MODE_NORMAL,
    MODE_REVIEW,
)


class V5ConfidenceCalibrationTests(unittest.TestCase):
    def test_result_confidence_uses_pipeline_quality_not_only_classification(self):
        result = calibrate_confidence(
            original_confidence=1.0,
            retrieval_expanded=False,
            self_evaluation_result={K_PASSED: True, K_ISSUES: []},
            response_mode=MODE_NORMAL,
            used_sources=True,
            answer_completeness={K_COMPLETENESS_SCORE: 0.6},
            risk_score=0,
        )

        self.assertLess(result, 1.0)
        self.assertGreater(result, 0.8)

    def test_missing_sources_and_low_completeness_reduce_result_confidence(self):
        result = calibrate_confidence(
            original_confidence=0.95,
            retrieval_expanded=False,
            self_evaluation_result={K_PASSED: False, K_ISSUES: ["no_used_sources"]},
            response_mode=MODE_NORMAL,
            used_sources=False,
            answer_completeness={K_COMPLETENESS_SCORE: 0.3},
            risk_score=2,
        )

        self.assertLess(result, 0.7)

    def test_review_and_blocked_modes_cap_result_confidence(self):
        review_result = calibrate_confidence(
            original_confidence=1.0,
            retrieval_expanded=False,
            self_evaluation_result={K_PASSED: True, K_ISSUES: []},
            response_mode=MODE_REVIEW,
            used_sources=True,
            answer_completeness={K_COMPLETENESS_SCORE: 1.0},
            risk_score=0,
        )
        blocked_result = calibrate_confidence(
            original_confidence=1.0,
            retrieval_expanded=False,
            self_evaluation_result={K_PASSED: True, K_ISSUES: []},
            response_mode=MODE_BLOCKED,
            used_sources=True,
            answer_completeness={K_COMPLETENESS_SCORE: 1.0},
            risk_score=0,
        )

        self.assertLessEqual(review_result, 0.75)
        self.assertLessEqual(blocked_result, 0.2)


if __name__ == "__main__":
    unittest.main()
