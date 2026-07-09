"""系统日志服务 —— 暂返回占位数据；后续对接 Python logging DB handler 或文件读取。"""


def list_logs(db, *, page: int = 1, page_size: int = 20) -> dict:
    """日志列表（占位）。"""
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
    }


def get_log(db, log_id: int) -> dict | None:
    """单条日志（占位）。"""
    return None
