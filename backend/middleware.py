from __future__ import annotations

import json
import traceback
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    detail = str(exc) if str(exc) else type(exc).__name__
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail, "type": type(exc).__name__},
    )


async def http_exception_handler(request: Request, exc: Any) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code if hasattr(exc, "status_code") else 500,
        content={"detail": exc.detail if hasattr(exc, "detail") else str(exc)},
    )


async def validation_exception_handler(request: Request, exc: Any) -> JSONResponse:
    errors = []
    if hasattr(exc, "errors"):
        for err in exc.errors():
            errors.append({"loc": err.get("loc", []), "msg": err.get("msg", "")})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "请求参数校验失败", "errors": errors},
    )


def register_exception_handlers(app: Any) -> None:
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
