"""Node Stream 门户 —— 处理节点 WebSocket 连接生命周期事件。

Part A 完成后切换真实实现：从 ``src.network.wss.node_handler`` 导入 ConnectionRegistry。
"""

from sqlalchemy.orm import Session


def handle_node_connected(db: Session, node_id: int) -> None:
    """节点连接建立后的处理入口。

    当前 Server 在握手响应中已直接推送已有设备，无需再做 LIST_DEVICES 交互。
    此函数作为后续 DEVICE_CHANGED 事件的入口点，当前仅记录日志。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Node %d connected", node_id)
