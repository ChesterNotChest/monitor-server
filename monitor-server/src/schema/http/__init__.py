"""HTTP Schema 包 —— REST 请求/响应 Pydantic 模型。"""

from .named_person import PersonCreate, PersonUpdate, PersonResponse, PersonListResponse

__all__ = ["PersonCreate", "PersonUpdate", "PersonResponse", "PersonListResponse"]
