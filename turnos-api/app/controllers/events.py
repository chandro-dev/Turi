"""CONTROLADOR - flujo de eventos en tiempo real (SSE). Publico: solo emite una senal sin datos."""
import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..services.events import broadcaster

router = APIRouter(prefix="/api", tags=["tiempo-real"])
KEEPALIVE_SECONDS = 20


@router.get("/events")
async def events(request: Request):
    broadcaster.bind(asyncio.get_running_loop())
    q = broadcaster.subscribe()

    async def stream():
        try:
            yield "retry: 3000\ndata: hello\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    kind = await asyncio.wait_for(q.get(), timeout=KEEPALIVE_SECONDS)
                    yield f"data: {kind}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"  # mantiene viva la conexion a traves de proxies
        finally:
            broadcaster.unsubscribe(q)

    return StreamingResponse(
        stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
