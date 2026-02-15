import asyncio

from fastapi import APIRouter, Request

from sonos_api.models.state import PlayerState, TrackInfo, ZoneInfo, MemberInfo
from sonos_api.utils.retry import retry_soco

router = APIRouter()


@retry_soco()
async def _get_track_info(speaker) -> TrackInfo:
    info = await asyncio.to_thread(speaker.get_current_track_info)
    return TrackInfo(
        title=info.get("title", ""),
        artist=info.get("artist", ""),
        album=info.get("album", ""),
        album_art=info.get("album_art_uri", ""),
        duration=info.get("duration", ""),
        position=info.get("position", ""),
        uri=info.get("uri", ""),
    )


@retry_soco()
async def _get_transport_state(speaker) -> str:
    info = await asyncio.to_thread(speaker.get_current_transport_info)
    return info.get("current_transport_state", "UNKNOWN")


@router.get("/{room}/state", response_model=PlayerState)
async def get_state(room: str, request: Request):
    """Get the current player state for a room."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404,
            content={"error": "Room not found", "detail": f"No speaker found for '{room}'"},
        )

    async with manager.get_lock(room):
        transport_state = await _get_transport_state(speaker)
        track = await _get_track_info(speaker)
        volume = await asyncio.to_thread(lambda: speaker.volume)
        mute = await asyncio.to_thread(lambda: speaker.mute)

    return PlayerState(
        room=room,
        state=transport_state,
        volume=volume,
        mute=mute,
        track=track,
    )


@router.get("/zones", response_model=list[ZoneInfo])
async def get_zones(request: Request):
    """Get all zone/group topology."""
    manager = request.app.state.speaker_manager
    speakers = manager.speakers

    if not speakers:
        return []

    # Use any speaker to get the full group topology
    any_speaker = next(iter(speakers.values()))
    try:
        groups = await asyncio.to_thread(lambda: any_speaker.all_groups)
    except Exception:
        return []

    zones = []
    for group in groups:
        coordinator = group.coordinator
        coord_name = await asyncio.to_thread(lambda c=coordinator: c.player_name)

        members = []
        for member in group.members:
            member_name = await asyncio.to_thread(lambda m=member: m.player_name)
            members.append(MemberInfo(room=member_name, uuid=member.uid))

        try:
            transport_state = await _get_transport_state(coordinator)
            volume = await asyncio.to_thread(lambda c=coordinator: c.volume)
            track = await _get_track_info(coordinator)
        except Exception:
            transport_state = "UNKNOWN"
            volume = 0
            track = TrackInfo()

        zones.append(
            ZoneInfo(
                coordinator=coord_name,
                uuid=coordinator.uid,
                members=members,
                state=transport_state,
                volume=volume,
                track=track,
            )
        )

    return zones
