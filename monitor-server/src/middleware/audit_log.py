"""API 操作审计中间件。"""

import logging
from urllib.parse import unquote

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.constants import API_PREFIX
from src.extensions import SessionLocal
from src.service import log_task
from src.service.auth_task import verify_token

logger = logging.getLogger(__name__)

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_EXCLUDED_PATHS = {f"{API_PREFIX}/auth/login/"}
_ACTION_LABELS = {
    "POST": "创建/提交",
    "PUT": "更新",
    "PATCH": "更新",
    "DELETE": "删除",
}


def _extract_bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def _normalize_path(path: str) -> str:
    return path if path.endswith("/") else f"{path}/"


def _target_from_path(path: str) -> tuple[str, str | None]:
    relative = path.removeprefix(API_PREFIX).strip("/")
    parts = [unquote(part) for part in relative.split("/") if part]
    if not parts:
        return "api", None
    target_type = parts[0].replace("-", "_")
    target_id = parts[1] if len(parts) > 1 and parts[1].isdigit() else None
    return target_type, target_id


def _operation_summary(method: str, path: str) -> str:
    label = _ACTION_LABELS.get(method, method)
    target_type, target_id = _target_from_path(path)
    suffix = f" #{target_id}" if target_id else ""
    return f"用户操作：{label} {target_type}{suffix}"


class AuditLogMiddleware(BaseHTTPMiddleware):
    """将成功的登录后写操作记录到 log_entries。"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if not self._should_record(request, response.status_code):
            return response

        token = _extract_bearer_token(request.headers.get("Authorization"))
        payload = verify_token(token) if token else None
        if not payload:
            return response

        try:
            operator_id = int(payload.get("sub") or 0) or None
        except (TypeError, ValueError):
            operator_id = None
        if operator_id is None:
            return response

        path = request.url.path
        target_type, target_id = _target_from_path(path)
        session_factory = getattr(request.app.state, "audit_log_session_factory", SessionLocal)
        db = session_factory()
        try:
            log_task.record_operation(
                db,
                operator_id=operator_id,
                action=request.method.lower(),
                target_type=target_type,
                target_id=target_id,
                summary=_operation_summary(request.method, path),
                details={
                    "method": request.method,
                    "path": path,
                    "query": str(request.url.query or ""),
                    "status_code": response.status_code,
                    "username": payload.get("username"),
                    "role": payload.get("role"),
                    "client_host": request.client.host if request.client else None,
                },
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to record operation log")
        finally:
            db.close()

        return response

    @staticmethod
    def _should_record(request: Request, status_code: int) -> bool:
        path = request.url.path
        if request.method not in _MUTATING_METHODS:
            return False
        if status_code >= 400:
            return False
        if not path.startswith(API_PREFIX):
            return False
        if _normalize_path(path) in _EXCLUDED_PATHS:
            return False
        return True
