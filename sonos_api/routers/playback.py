import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from sonos_api.utils.retry import retry_soco

router = APIRouter()


def _get_speaker_or_404(request: Request, room: str):
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return None, manager
    return speaker, manager


@router.post("/{room}/play")
async def play(room: str, request: Request):
    """Resume playback."""
    speaker, manager = _get_speaker_or_404(request, room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _play():
        await asyncio.to_thread(speaker.play)

    async with manager.get_lock(room):
        await _play()
    return {"status": "ok"}


@router.post("/{room}/pause")
async def pause(room: str, request: Request):
    """Pause playback."""
    speaker, manager = _get_speaker_or_404(request, room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _pause():
        await asyncio.to_thread(speaker.pause)

    async with manager.get_lock(room):
        await _pause()
    return {"status": "ok"}


@router.post("/{room}/playpause")
async def playpause(room: str, request: Request):
    """Toggle play/pause."""
    speaker, manager = _get_speaker_or_404(request, room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _toggle():
        info = await asyncio.to_thread(speaker.get_current_transport_info)
        state = info.get("current_transport_state", "")
        if state == "PLAYING":
            await asyncio.to_thread(speaker.pause)
        else:
            await asyncio.to_thread(speaker.play)

    async with manager.get_lock(room):
        await _toggle()
    return {"status": "ok"}


@router.post("/{room}/next")
async def next_track(room: str, request: Request):
    """Skip to next track."""
    speaker, manager = _get_speaker_or_404(request, room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _next():
        await asyncio.to_thread(speaker.next)

    async with manager.get_lock(room):
        await _next()
    return {"status": "ok"}


@router.post("/{room}/previous")
async def previous_track(room: str, request: Request):
    """Go to previous track."""
    speaker, manager = _get_speaker_or_404(request, room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _prev():
        await asyncio.to_thread(speaker.previous)

    async with manager.get_lock(room):
        await _prev()
    return {"status": "ok"}
