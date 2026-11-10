from typing import Any, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.i18n import get_preferred_language, t


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message_key: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Any] = None,
        msg_kwargs: Optional[dict] = None,
    ):
        self.code = code
        self.message_key = message_key
        self.status_code = status_code
        self.details = details
        self.msg_kwargs = msg_kwargs or {}
        super().__init__(message_key)


class NotFoundError(AppException):
    def __init__(self, message_key: str = "resource_not_found", details: Optional[Any] = None, **kwargs):
        super().__init__(
            code="NOT_FOUND",
            message_key=message_key,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            msg_kwargs=kwargs,
        )


class ConflictError(AppException):
    def __init__(self, message_key: str = "conflict_error", details: Optional[Any] = None, **kwargs):
        super().__init__(
            code="CONFLICT",
            message_key=message_key,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
            msg_kwargs=kwargs,
        )


class PermissionDeniedError(AppException):
    def __init__(self, message_key: str = "permission_denied", details: Optional[Any] = None, **kwargs):
        super().__init__(
            code="PERMISSION_DENIED",
            message_key=message_key,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
            msg_kwargs=kwargs,
        )


class AuthenticationError(AppException):
    def __init__(self, message_key: str = "auth_invalid_credentials", details: Optional[Any] = None, **kwargs):
        super().__init__(
            code="UNAUTHORIZED",
            message_key=message_key,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            msg_kwargs=kwargs,
        )


class BadRequestError(AppException):
    def __init__(self, message_key: str = "validation_error", details: Optional[Any] = None, **kwargs):
        super().__init__(
            code="BAD_REQUEST",
            message_key=message_key,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            msg_kwargs=kwargs,
        )


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        lang = get_preferred_language(request)
        message = t(exc.message_key, lang=lang, **exc.msg_kwargs)
        payload = {
            "code": exc.code,
            "message": message,
        }
        if exc.details is not None:
            payload["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        lang = get_preferred_language(request)
        message = t("validation_error", lang=lang)
        errors = []
        for err in exc.errors():
            loc = " -> ".join([str(x) for x in err.get("loc", [])])
            errors.append({"field": loc, "msg": err.get("msg"), "type": err.get("type")})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "VALIDATION_ERROR",
                "message": message,
                "details": errors,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        # Never expose internal traceback to client
        lang = get_preferred_language(request)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred. Please contact support." if lang == "en" else "حدث خطأ داخلي في الخادم. يرجى الاتصال بالدعم الفني.",
            },
        )

