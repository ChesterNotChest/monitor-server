"""命名人物 Repository。"""

from src.models.named_person import NamedPerson
from .base import BaseRepo


class NamedPersonRepo(BaseRepo[NamedPerson]):
    model = NamedPerson
