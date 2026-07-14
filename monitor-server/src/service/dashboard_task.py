"""态势仪表板服务 —— 聚合查询。"""

from sqlalchemy.orm import Session

from src.repository.monitor_view_repo import MonitorViewRepo
from src.repository.situation_event_repo import SituationEventRepo
from src.repository.node_repo import NodeRepo


def get_stats(db: Session) -> dict:
    """实时聚合态势数据。"""
    view_count = MonitorViewRepo(db).count()
    alert_count = SituationEventRepo(db).count()
    node_repo = NodeRepo(db)

    # 在线 Node 数：需查 node 表的 is_connected 字段（Part A 模型变更后生效）
    online_nodes = 0
    try:
        online_nodes = db.query(node_repo.model).filter(
            node_repo.model.is_connected == True
        ).count()
    except AttributeError:
        # is_connected 字段尚未添加时的 fallback
        online_nodes = node_repo.count()

    return {
        "total_views": view_count,
        "active_alerts": alert_count,
        "online_nodes": online_nodes,
        "total_devices": 0,  # 待后续基于 Node 设备统计
    }


def get_trends(db: Session) -> dict:
    """最近 7 天告警趋势（按严重级别 × 日期聚合）。"""
    from collections import defaultdict
    from datetime import date, datetime, time, timedelta
    from src.repository.situation_event_repo import SituationEventRepo

    repo = SituationEventRepo(db)
    recent = repo.all(limit=500)

    # 按 (date, severity) 聚合
    buckets: dict[tuple[date, str], int] = defaultdict(int)
    for e in recent:
        if e.timestamp is None:
            continue
        sev = _trend_severity(e)
        day = e.timestamp.date() if hasattr(e.timestamp, 'date') else e.timestamp.date()
        buckets[(day, sev)] += 1

    # 过去 7 天
    today = date.today()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    points = []
    for d in days:
        for sev in ["INFO", "WARNING", "CRITICAL", "EMERGENCY"]:
            cnt = buckets.get((d, sev), 0)
            if cnt > 0:
                points.append({"date": d.isoformat(), "severity": sev, "count": cnt})
        # 确保每天至少一个点（避免图表空洞）
        if not any(p["date"] == d.isoformat() for p in points):
            points.append({"date": d.isoformat(), "severity": "INFO", "count": 0})
    return {"points": points}


def _trend_severity(e) -> str:
    """从 SituationEvent 提取可读严重级别。"""
    try:
        if e.exception and e.exception.severity:
            return e.exception.severity.name
    except Exception:
        pass
    return "WARNING"
