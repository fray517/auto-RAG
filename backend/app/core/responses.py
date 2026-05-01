"""Общие классы HTTP-ответов."""

from fastapi.responses import JSONResponse


class Utf8JSONResponse(JSONResponse):
    """JSONResponse с явным charset для Windows PowerShell."""

    media_type = "application/json; charset=utf-8"
