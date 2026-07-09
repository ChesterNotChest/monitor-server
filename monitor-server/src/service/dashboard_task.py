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
    """最近 7 天告警趋势（按严重级别分组）。"""
    # 当前返回占位数据；后续基于 SituationEvent.exception.severity 聚合
    from src.repository.situation_event_repo import SituationEventRepo
    repo = SituationEventRepo(db)
    recent = repo.all(limit=50)
    return {
        "points": [
            {"date": str(e.timestamp.date()) if e.timestamp else "", "severity": "unknown", "count": 1}
            for e in recent
        ]
    }
