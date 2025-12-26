from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse


class SimpleCorsMiddleware:
    """Minimal CORS for local dev.

    Allows browser calls from Vite dev server to this async service.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Handle preflight early
        if request.method == "OPTIONS":
            response = HttpResponse(status=200)
        else:
            response = self.get_response(request)

        origin = request.headers.get("Origin")
        if origin in {"http://localhost:3000", "http://127.0.0.1:3000"}:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"

        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        response["Access-Control-Max-Age"] = "600"
        return response
