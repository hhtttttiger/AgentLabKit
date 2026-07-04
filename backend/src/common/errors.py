from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .response import fail


class BusinessError(Exception):
    def __init__(self, msg: str, status_code: int = 400):
        self.msg = msg
        self.status_code = status_code
        super().__init__(msg)


class NotFoundError(BusinessError):
    def __init__(self, resource: str, key: str = ""):
        msg = f"{resource} not found" + (f": {key}" if key else "")
        super().__init__(msg, status_code=404)


class ConflictError(BusinessError):
    def __init__(self, msg: str = "Resource conflict"):
        super().__init__(msg, status_code=409)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def handle_business_error(request: Request, exc: BusinessError):
        return fail(exc.msg, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def handle_generic_error(request: Request, exc: Exception):
        import logging

        logging.getLogger(__name__).exception("Unhandled error")
        return fail("Internal server error", status_code=500)
