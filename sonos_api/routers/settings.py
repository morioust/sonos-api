import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sonos_api.utils.retry import retry_soco

router = APIRouter()


class PlayModeRequest(BaseModel):
    shuffle: bool | None = None
    repeat: str | None = None  # "off", "one", "all"


class SeekRequest(BaseModel):
    position: int | None = None  # seconds
    track: int | None = None  # track number (1-based)


class SleepTimerRequest(BaseModel):
    seconds: int  # 0 to cancel


# Play mode mapping: (shuffle, repeat) -> SoCo play_mode string
_PLAY_MODES = {
    (False, "off"): "NORMAL",
    (True, "off"): "SHUFFLE_NOREPEAT",
    (False, "all"): "REPEAT_ALL",
    (True, "all"): "SHUFFLE",
    (False, "one"): "REPEAT_ONE",
    (True, "one"): "SHUFFLE_REPEAT_ONE",
}


@router.put("/{room}/playmode")
async def set_playmode(room: str, body: PlayModeRequest, request: Request):
    """Set play mode (shuffle/repeat)."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _set():
        current_mode = await asyncio.to_thread(lambda: speaker.play_mode)
        # Parse current mode
        cur_shuffle = "SHUFFLE" in current_mode
        if "REPEAT_ONE" in current_mode:
            cur_repeat = "one"
        elif "REPEAT" in current_mode or current_mode == "SHUFFLE":
            cur_repeat = "all"
        else:
            cur_repeat = "off"

        new_shuffle = body.shuffle if body.shuffle is not None else cur_shuffle
        new_repeat = body.repeat if body.repeat is not None else cur_repeat

        mode = _PLAY_MODES.get((new_shuffle, new_repeat), "NORMAL")
        await asyncio.to_thread(lambda: setattr(speaker, "play_mode", mode))
        return {"shuffle": new_shuffle, "repeat": new_repeat, "mode": mode}

    async with manager.get_lock(room):
        result = await _set()
    return {"status": "ok", **result}


@router.post("/{room}/seek")
async def seek(room: str, body: SeekRequest, request: Request):
    """Seek to position (seconds) or track number."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    if body.position is None and body.track is None:
        return JSONResponse(
            status_code=400,
            content={"error": "Must specify 'position' (seconds) or 'track' (number)"},
        )

    @retry_soco()
    async def _seek():
        if body.track is not None:
            await asyncio.to_thread(lambda: speaker.play_from_queue(body.track - 1))
        elif body.position is not None:
            h = body.position // 3600
            m = (body.position % 3600) // 60
            s = body.position % 60
            timestamp = f"{h}:{m:02d}:{s:02d}"
            await asyncio.to_thread(lambda: speaker.seek(timestamp))

    async with manager.get_lock(room):
        await _seek()
    return {"status": "ok"}


@router.put("/{room}/sleep")
async def set_sleep_timer(room: str, body: SleepTimerRequest, request: Request):
    """Set sleep timer (seconds). Use 0 to cancel."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _set():
        duration = None if body.seconds == 0 else body.seconds
        await asyncio.to_thread(lambda: speaker.set_sleep_timer(duration))

    async with manager.get_lock(room):
        await _set()
    return {"status": "ok", "seconds": body.seconds}
