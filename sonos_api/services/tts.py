import asyncio
import hashlib
import logging
from pathlib import Path

from sonos_api.config import settings

logger = logging.getLogger(__name__)


async def generate_tts(text: str, language: str = "en") -> str:
    """Generate a TTS audio file using gTTS. Returns the filename."""
    # Deterministic filename based on text + language for caching
    key = f"{language}:{text}"
    filename = hashlib.md5(key.encode()).hexdigest() + ".mp3"
    cache_dir = Path(settings.tts_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    filepath = cache_dir / filename

    if filepath.exists():
        logger.debug("TTS cache hit: %s", filename)
        return filename

    def _generate():
        from gtts import gTTS

        tts = gTTS(text=text, lang=language)
        tts.save(str(filepath))

    await asyncio.to_thread(_generate)
    logger.info("Generated TTS: %s -> %s", text[:50], filename)
    return filename


async def announce(speaker, text: str, language: str = "en", volume: int | None = None, host_ip: str = ""):
    """Play a TTS announcement on a speaker, restoring state afterwards."""
    filename = await generate_tts(text, language)

    def _do_announce():
        # Save current state
        prev_volume = speaker.volume
        prev_mute = speaker.mute
        transport = speaker.get_current_transport_info()
        was_playing = transport.get("current_transport_state") == "PLAYING"

        try:
            # Set announcement volume
            if volume is not None:
                speaker.volume = volume
            if speaker.mute:
                speaker.mute = False

            # Build URI — the FastAPI static mount serves from tts_cache_dir
            uri = f"http://{host_ip}:{settings.api_port}/static/{filename}"
            speaker.play_uri(uri, title="Announcement")

            # Wait for it to finish (poll transport state)
            import time

            time.sleep(1)  # Give it a moment to start
            for _ in range(60):  # Max 60 seconds
                info = speaker.get_current_transport_info()
                state = info.get("current_transport_state", "")
                if state in ("STOPPED", "PAUSED_PLAYBACK"):
                    break
                time.sleep(1)
        finally:
            # Restore state
            speaker.volume = prev_volume
            speaker.mute = prev_mute
            if was_playing:
                try:
                    speaker.play()
                except Exception:
                    pass  # Previous track may no longer be available

    await asyncio.to_thread(_do_announce)
