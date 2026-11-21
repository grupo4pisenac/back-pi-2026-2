import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request, status

from app.core.config import settings


class InMemoryRateLimiter:
    """Rate limiter leve em memória (janela deslizante por IP), injetável via Depends."""

    def __init__(self, max_requests: int | None = None, window_seconds: int | None = None) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._hits.clear()

    @staticmethod
    def _extract_client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def __call__(self, request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        max_req = (
            self._max_requests
            if self._max_requests is not None
            else settings.FORGOT_PASSWORD_RATE_LIMIT_MAX_REQUESTS
        )
        window = (
            self._window_seconds
            if self._window_seconds is not None
            else settings.FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS
        )

        agora = time.monotonic()
        chave = self._extract_client_ip(request)
        fila = self._hits[chave]

        while fila and agora - fila[0] >= window:
            fila.popleft()

        if len(fila) >= max_req:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas solicitações. Tente novamente mais tarde.",
            )

        fila.append(agora)


forgot_password_rate_limiter = InMemoryRateLimiter()
reset_password_rate_limiter = InMemoryRateLimiter()
