import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sonos_api.utils.retry import retry_soco

router = APIRouter()


class VolumeRequest(BaseModel):
    volume: int | str  # absolute int or "+5"/"-5"


@router.put("/{room}/volume")
async def set_volume(room: str, body: VolumeRequest, request: Request):
    """Set volume (absolute or relative)."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _set_vol():
        vol = body.volume
        if isinstance(vol, str):
            current = await asyncio.to_thread(lambda: speaker.volume)
            target = current + int(vol)
        else:
            target = vol
        target = max(0, min(100, target))
        await asyncio.to_thread(lambda: setattr(speaker, "volume", target))
        return target

    async with manager.get_lock(room):
        new_vol = await _set_vol()
    return {"status": "ok", "volume": new_vol}


@router.post("/{room}/mute")
async def mute(room: str, request: Request):
    """Mute speaker."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _mute():
        await asyncio.to_thread(lambda: setattr(speaker, "mute", True))

    async with manager.get_lock(room):
        await _mute()
    return {"status": "ok", "mute": True}


@router.post("/{room}/unmute")
async def unmute(room: str, request: Request):
    """Unmute speaker."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _unmute():
        await asyncio.to_thread(lambda: setattr(speaker, "mute", False))

    async with manager.get_lock(room):
        await _unmute()
    return {"status": "ok", "mute": False}


@router.post("/{room}/togglemute")
async def togglemute(room: str, request: Request):
    """Toggle mute."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _toggle():
        current = await asyncio.to_thread(lambda: speaker.mute)
        new_mute = not current
        await asyncio.to_thread(lambda: setattr(speaker, "mute", new_mute))
        return new_mute

    async with manager.get_lock(room):
        new_mute = await _toggle()
    return {"status": "ok", "mute": new_mute}
