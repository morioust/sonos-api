import asyncio
import logging

import soco

from sonos_api.utils.speaker import normalize_room_name

logger = logging.getLogger(__name__)


class SpeakerManager:
    """Manages discovered Sonos speakers with background re-discovery."""

    def __init__(self, discovery_interval: int = 30) -> None:
        self._discovery_interval = discovery_interval
        self._speakers: dict[str, soco.SoCo] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._discovery_task: asyncio.Task | None = None

    @property
    def speakers(self) -> dict[str, soco.SoCo]:
        return dict(self._speakers)

    async def start(self) -> None:
        """Run initial discovery and start background task."""
        await self._discover()
        self._discovery_task = asyncio.create_task(self._discovery_loop())

    async def stop(self) -> None:
        """Stop background discovery."""
        if self._discovery_task:
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass

    async def _discover(self) -> None:
        """Discover Sonos speakers on the network."""
        try:
            devices = await asyncio.to_thread(soco.discover, timeout=5)
        except Exception:
            logger.exception("Discovery failed")
            return

        if not devices:
            logger.warning("No Sonos devices found")
            return

        found: dict[str, soco.SoCo] = {}
        for device in devices:
            try:
                name = await asyncio.to_thread(lambda d=device: d.player_name)
                normalized = normalize_room_name(name)
                found[normalized] = device
                if normalized not in self._locks:
                    self._locks[normalized] = asyncio.Lock()
            except Exception:
                logger.exception("Failed to get player name for %s", device.ip_address)

        self._speakers = found
        logger.info("Discovered %d speakers: %s", len(found), list(found.keys()))

    async def _discovery_loop(self) -> None:
        """Periodically re-discover speakers."""
        while True:
            await asyncio.sleep(self._discovery_interval)
            await self._discover()

    def get(self, room: str) -> soco.SoCo | None:
        """Get a speaker by normalized room name."""
        return self._speakers.get(normalize_room_name(room))

    def get_lock(self, room: str) -> asyncio.Lock:
        """Get the per-device lock for a room."""
        normalized = normalize_room_name(room)
        if normalized not in self._locks:
            self._locks[normalized] = asyncio.Lock()
        return self._locks[normalized]

    async def trigger_rediscovery(self) -> None:
        """Trigger an immediate re-discovery (e.g. after a device becomes unreachable)."""
        await self._discover()
