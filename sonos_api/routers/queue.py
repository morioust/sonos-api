import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sonos_api.models.state import TrackInfo
from sonos_api.utils.retry import retry_soco

router = APIRouter()


class QueueItem(BaseModel):
    position: int
    title: str = ""
    artist: str = ""
    album: str = ""
    album_art: str = ""
    uri: str = ""


class QueueResponse(BaseModel):
    room: str
    total: int
    items: list[QueueItem]


@router.get("/{room}/queue", response_model=QueueResponse)
async def get_queue(room: str, request: Request):
    """Get current queue."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _get():
        return await asyncio.to_thread(speaker.get_queue, max_items=1000)

    async with manager.get_lock(room):
        queue = await _get()

    items = [
        QueueItem(
            position=i + 1,
            title=getattr(item, "title", ""),
            artist=getattr(item, "creator", ""),
            album=getattr(item, "album", ""),
            album_art=getattr(item, "album_art_uri", ""),
            uri=getattr(item, "resources", [{}])[0].uri if getattr(item, "resources", []) else "",
        )
        for i, item in enumerate(queue)
    ]

    return QueueResponse(room=room, total=len(items), items=items)


@router.delete("/{room}/queue")
async def clear_queue(room: str, request: Request):
    """Clear the queue."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _clear():
        await asyncio.to_thread(speaker.clear_queue)

    async with manager.get_lock(room):
        await _clear()
    return {"status": "ok"}
