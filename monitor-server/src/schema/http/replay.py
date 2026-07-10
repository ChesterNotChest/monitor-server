"""录制回放 Schema。"""

from datetime import datetime

from pydantic import BaseModel


class RecordingResponse(BaseModel):
    """录制记录响应体。"""

    id: int
    view_id: int
    file_path: str
    start_time: datetime
    end_time: datetime | None

    model_config = {"from_attributes": True}
