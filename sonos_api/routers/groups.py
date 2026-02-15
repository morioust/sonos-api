import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sonos_api.utils.retry import retry_soco

router = APIRouter()


class GroupVolumeRequest(BaseModel):
    volume: int | str  # absolute int or "+5"/"-5"


@router.post("/{room}/join/{other}")
async def join_group(room: str, other: str, request: Request):
    """Join {room} to {other}'s group. {other} becomes/stays the coordinator."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    target = manager.get(other)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})
    if not target:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": other})

    @retry_soco()
    async def _join():
        await asyncio.to_thread(speaker.join, target)

    async with manager.get_lock(room):
        await _join()
    return {"status": "ok", "room": room, "joined": other}


@router.post("/{room}/leave")
async def leave_group(room: str, request: Request):
    """Remove {room} from its current group."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _leave():
        await asyncio.to_thread(speaker.unjoin)

    async with manager.get_lock(room):
        await _leave()
    return {"status": "ok", "room": room}


@router.put("/{room}/groupvolume")
async def set_group_volume(room: str, body: GroupVolumeRequest, request: Request):
    """Set volume for the entire group that {room} belongs to."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _set():
        group = await asyncio.to_thread(lambda: speaker.group)
        if not group:
            return None

        vol = body.volume
        if isinstance(vol, str):
            current = await asyncio.to_thread(lambda: group.volume)
            target = current + int(vol)
        else:
            target = vol
        target = max(0, min(100, target))
        await asyncio.to_thread(lambda: setattr(group, "volume", target))
        return target

    async with manager.get_lock(room):
        new_vol = await _set()

    if new_vol is None:
        return JSONResponse(status_code=400, content={"error": "Speaker not in a group"})
    return {"status": "ok", "volume": new_vol}
