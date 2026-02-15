import asyncio
import socket

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sonos_api.services.tts import announce
from sonos_api.utils.retry import retry_soco

router = APIRouter()


class SayRequest(BaseModel):
    text: str
    language: str = "en"
    volume: int | None = None


def _get_host_ip() -> str:
    """Get the local IP address that can reach the network."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@router.post("/{room}/say")
async def say(room: str, body: SayRequest, request: Request):
    """Play a TTS announcement."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    host_ip = _get_host_ip()

    async with manager.get_lock(room):
        await announce(speaker, body.text, body.language, body.volume, host_ip)

    return {"status": "ok", "text": body.text}
