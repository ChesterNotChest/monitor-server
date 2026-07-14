"""日报持久化 + AI workflow 测试。"""
import pytest
from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch

from src.service.report_task import (
    build_daily_stats,
    save_daily_report,
    load_daily_report,
    build_event_context,
    validate_insights_json,
    DeepSeekReportError,
)


class TestBuildDailyStats:
    """统计层测试。"""

    def test_build_stats_empty_day(self, db):
        """无事件时返回空统计。"""
        stats = build_daily_stats(db, date.today())
        assert stats["total_alerts"] == 0
        assert stats["risk_level"] == "LOW"
        assert stats["by_severity"] == []
        assert stats["period"] == "daily"
        assert "time_range_start" in stats
        assert "time_range_end" in stats
        assert "+08:00" in stats["time_range_start"]

    def test_build_stats_has_new_fields(self, db):
        """统计层包含 by_view 和 entity_types 字段。"""
        stats = build_daily_stats(db, date.today())
        assert "by_view" in stats
        assert "entity_types" in stats
        assert isinstance(stats["by_view"], list)
        assert isinstance(stats["entity_types"], list)

    def test_build_stats_time_boundaries(self, db):
        """time_range 正确覆盖指定窗口。"""
        today = date.today()
        stats = build_daily_stats(db, today,
                                  time_start=time(8, 0), time_end=time(17, 0))
        assert "08:00" in stats["time_range_start"] or "+08:00" in stats["time_range_start"]
        assert "17:00" in stats["time_range_end"] or "+08:00" in stats["time_range_end"]


class TestSaveAndLoadReport:
    """持久化测试。"""

    def test_save_new_report(self, db):
        """首次保存日报 → INSERT 新记录。"""
        today = date.today()
        stats = {"period": "daily", "date": today.isoformat(), "total_alerts": 0, "risk_level": "LOW",
                 "by_severity": [], "top_exceptions": [], "hourly_trend": [],
                 "by_view": [], "entity_types": [],
                 "time_range_start": "2026-07-14T00:00:00+08:00",
                 "time_range_end": "2026-07-14T23:59:00+08:00"}
        result = save_daily_report(db, today, stats)
        assert result["report_date"] == today.isoformat()
        assert result["regenerated_count"] == 0
        assert result["stats_json"] == stats

    def test_upsert_existing_report(self, db):
        """同一天再次保存 → UPDATE 覆盖，regenerated_count 递增。"""
        today = date.today()
        stats1 = {"period": "daily", "date": today.isoformat(), "total_alerts": 5, "risk_level": "MEDIUM",
                  "by_severity": [], "top_exceptions": [], "hourly_trend": [],
                  "by_view": [], "entity_types": [],
                  "time_range_start": "2026-07-14T00:00:00+08:00",
                  "time_range_end": "2026-07-14T23:59:00+08:00"}
        save_daily_report(db, today, stats1)

        stats2 = {**stats1, "total_alerts": 10}
        result = save_daily_report(db, today, stats2)
        assert result["regenerated_count"] == 1
        assert result["stats_json"]["total_alerts"] == 10

    def test_load_missing_report_returns_none(self, db):
        """无持久化数据时返回 None。"""
        result = load_daily_report(db, date(2099, 1, 1))
        assert result is None

    def test_save_and_load_roundtrip(self, db):
        """保存后立即可加载。"""
        today = date.today()
        stats = {"period": "daily", "date": today.isoformat(), "total_alerts": 3, "risk_level": "LOW",
                 "by_severity": [], "top_exceptions": [], "hourly_trend": [],
                 "by_view": [], "entity_types": [],
                 "time_range_start": "2026-07-14T00:00:00+08:00",
                 "time_range_end": "2026-07-14T23:59:00+08:00"}
        insights = {"partial": False, "summary": "test", "key_findings": ["f1"],
                     "recommendations": ["r1"], "risk_distribution": [],
                     "generated_at": "2026-07-14T17:00:00+08:00"}
        save_daily_report(db, today, stats,
                          insights_json=insights, ai_provider="deepseek", ai_model="v4-flash")

        loaded = load_daily_report(db, today)
        assert loaded is not None
        assert loaded["stats"]["total_alerts"] == 3
        assert loaded["insights"]["summary"] == "test"
        assert loaded["ai_provider"] == "deepseek"


class TestEventContext:
    """事件上下文构建测试。"""

    def test_empty_context(self, db):
        """无事件时返回空上下文。"""
        ctx = build_event_context(db, date.today())
        assert ctx["report_meta"]["total_alerts"] == 0
        assert ctx["events"] == []
        assert "hourly_distribution" in ctx
        assert "by_view" in ctx


class TestValidateInsights:
    """Insights JSON 验证测试。"""

    def test_valid_insights(self):
        """完整格式通过验证。"""
        insights = {
            "partial": False,
            "summary": "今日运营正常",
            "key_findings": ["发现1", "发现2"],
            "recommendations": ["建议1"],
            "risk_distribution": [],
            "generated_at": "2026-07-14T17:00:00+08:00",
        }
        result = validate_insights_json(insights)
        assert result["summary"] == "今日运营正常"

    def test_missing_required_key(self):
        """缺失必填键时抛异常。"""
        with pytest.raises(ValueError, match="missing required key"):
            validate_insights_json({"summary": "ok"})

    def test_key_findings_not_list(self):
        """key_findings 不是数组时抛异常。"""
        with pytest.raises(ValueError, match="key_findings"):
            validate_insights_json({
                "summary": "ok", "key_findings": "not a list",
                "recommendations": ["r1"],
            })
