from src.constants import API_PREFIX


def test_daily_report_endpoint_empty(client, admin_headers):
    resp = client.get(f"{API_PREFIX}/reports/daily/?date=2026-07-12", headers=admin_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "daily"
    assert data["date"] == "2026-07-12"
    assert data["total_alerts"] == 0
    assert data["risk_level"] == "LOW"


def test_deepseek_daily_report_endpoint(client, admin_headers, monkeypatch):
    def fake_get_deepseek_daily_report(db, api_key, target_date=None, model=None):
        assert api_key == "sk-test"
        assert model == "deepseek-v4-flash"
        return {
            "period": "daily",
            "date": "2026-07-12",
            "total_alerts": 0,
            "risk_level": "LOW",
            "summary": "DeepSeek summary",
            "key_findings": ["finding"],
            "recommendations": ["recommendation"],
            "by_severity": [],
            "top_exceptions": [],
            "hourly_trend": [],
            "ai_provider": "deepseek",
            "ai_model": "deepseek-v4-flash",
            "ai_generated": True,
        }

    from src.service import report_task

    monkeypatch.setattr(report_task, "get_deepseek_daily_report", fake_get_deepseek_daily_report)

    resp = client.post(
        f"{API_PREFIX}/reports/daily/deepseek",
        headers=admin_headers,
        json={
            "date": "2026-07-12",
            "api_key": "sk-test",
            "model": "deepseek-v4-flash",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == "DeepSeek summary"
    assert data["ai_provider"] == "deepseek"
    assert data["ai_generated"] is True


def test_deepseek_daily_report_requires_key(client, admin_headers):
    resp = client.post(
        f"{API_PREFIX}/reports/daily/deepseek",
        headers=admin_headers,
        json={"date": "2026-07-12", "api_key": "   "},
    )

    assert resp.status_code == 400
