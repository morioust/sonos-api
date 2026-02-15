import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sonos_api.utils.retry import retry_soco

router = APIRouter()


class EqualizerRequest(BaseModel):
    bass: int | None = None  # -10 to 10
    treble: int | None = None  # -10 to 10


@router.put("/{room}/equalizer")
async def set_equalizer(room: str, body: EqualizerRequest, request: Request):
    """Set bass and/or treble (-10 to 10)."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _set():
        result = {}
        if body.bass is not None:
            val = max(-10, min(10, body.bass))
            await asyncio.to_thread(lambda: setattr(speaker, "bass", val))
            result["bass"] = val
        if body.treble is not None:
            val = max(-10, min(10, body.treble))
            await asyncio.to_thread(lambda: setattr(speaker, "treble", val))
            result["treble"] = val
        return result

    async with manager.get_lock(room):
        result = await _set()
    return {"status": "ok", **result}
