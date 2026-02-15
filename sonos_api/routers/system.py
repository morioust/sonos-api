import asyncio

from fastapi import APIRouter, Request

from sonos_api.models.state import HealthResponse
from sonos_api.utils.retry import retry_soco

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    """Health check with device count."""
    manager = request.app.state.speaker_manager
    return HealthResponse(
        status="ok",
        speakers=len(manager.speakers),
    )


@router.post("/pauseall")
async def pause_all(request: Request):
    """Pause all zones."""
    manager = request.app.state.speaker_manager
    speakers = manager.speakers
    paused = []

    for name, speaker in speakers.items():

        @retry_soco()
        async def _pause(s=speaker):
            info = await asyncio.to_thread(s.get_current_transport_info)
            if info.get("current_transport_state") == "PLAYING":
                await asyncio.to_thread(s.pause)
                return True
            return False

        try:
            async with manager.get_lock(name):
                if await _pause():
                    paused.append(name)
        except Exception:
            pass

    return {"status": "ok", "paused": paused}


@router.post("/resumeall")
async def resume_all(request: Request):
    """Resume all zones."""
    manager = request.app.state.speaker_manager
    speakers = manager.speakers
    resumed = []

    for name, speaker in speakers.items():

        @retry_soco()
        async def _resume(s=speaker):
            info = await asyncio.to_thread(s.get_current_transport_info)
            if info.get("current_transport_state") == "PAUSED_PLAYBACK":
                await asyncio.to_thread(s.play)
                return True
            return False

        try:
            async with manager.get_lock(name):
                if await _resume():
                    resumed.append(name)
        except Exception:
            pass

    return {"status": "ok", "resumed": resumed}
