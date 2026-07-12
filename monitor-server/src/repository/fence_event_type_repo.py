"""电子围栏事件类型 Repository。"""

from .base import BaseRepo
from ..models.fence_event_type import FenceEventType


class FenceEventTypeRepo(BaseRepo[FenceEventType]):
    """电子围栏事件类型数据访问层。"""

    model = FenceEventType
