"""Unit tests — DetectionAgent."""

import pytest

from tests.helpers import detect_harbourview_p1


@pytest.mark.unit
class TestDetection:
    def test_harbourview_p1_cross_source_compounding(self, rules):
        _, hv, det, _ = detect_harbourview_p1(rules)
        assert len(hv) >= 1
        assert det is not None
        assert det.compounding is not None
        assert det.cross_source is not None
        assert det.priority == "P1"
