"""
Audit logging middleware for the Offline LLM Assistant.
"""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..database import SessionLocal
from .. import models


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to record API requests and responses to the audit_events table.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.time()

        user_id = None

        # Execute request
        response: Response = await call_next(request)
        process_time = round(time.time() - start_time, 4)

        # Skip logging health checks to prevent log flooding
        if request.url.path == "/health":
            return response

        audit_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_sec": process_time,
            "ip_address": request.client.host if request.client else "127.0.0.1",
        }

        try:
            db = SessionLocal()
            audit_entry = models.AuditEvent(
                actor_id=user_id,
                action=f"{request.method} {request.url.path}",
                object_type="api_endpoint",
                object_id=request_id,
                result="success" if 200 <= response.status_code < 400 else "failure",
                timestamp=datetime.now(timezone.utc),
                request_id=request_id,
                details=json.dumps(audit_data),
            )
            db.add(audit_entry)
            db.commit()
            db.close()
        except Exception:
            pass

        return response