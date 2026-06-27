from app.issue_detail import audit_timeline, channel_label


def test_channel_label():
    assert channel_label("public_review") == "Public Review"
    assert channel_label("kpi_email") == "Staff KPI Email"


def test_audit_timeline_scoring():
    rows = [
        {
            "classification": {
                "stage": "scoring",
                "primary_theme": "projection_quality",
                "sentiment": {"projection_quality": "negative"},
            },
            "score": 0.85,
            "rules_version": "1.3",
        }
    ]
    timeline = audit_timeline(rows)
    assert timeline[0]["stage"] == "Classification"
    assert "projection" in timeline[0]["detail"].lower()
