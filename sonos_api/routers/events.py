import asyncio
import json
import logging

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple broadcast: connected clients subscribe to this set
_clients: set[asyncio.Queue] = set()


def broadcast(event: str, data: dict) -> None:
    """Send an event to all connected SSE clients."""
    message = {"event": event, "data": json.dumps(data)}
    for q in _clients.copy():
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            pass  # Drop events for slow clients


@router.get("/events")
async def sse_events(request: Request):
    """Server-Sent Events stream for real-time updates."""
    q: asyncio.Queue = asyncio.Queue(maxsize=64)
    _clients.add(q)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield message
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield {"comment": "keepalive"}
        finally:
            _clients.discard(q)

    return EventSourceResponse(event_generator())
