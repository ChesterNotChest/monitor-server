"""用户 Repository。"""

from .base import BaseRepo
from ..models.user import User


class UserRepo(BaseRepo[User]):
    model = User
