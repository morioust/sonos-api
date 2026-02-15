import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sonos_api.utils.retry import retry_soco

router = APIRouter()


class FavoriteItem(BaseModel):
    title: str
    uri: str = ""
    meta: str = ""


class FavoritesResponse(BaseModel):
    total: int
    items: list[FavoriteItem]


@router.get("/favorites", response_model=FavoritesResponse)
async def get_favorites(request: Request):
    """List Sonos favorites."""
    manager = request.app.state.speaker_manager
    speakers = manager.speakers
    if not speakers:
        return JSONResponse(status_code=503, content={"error": "No speakers available"})

    any_speaker = next(iter(speakers.values()))

    @retry_soco()
    async def _get():
        return await asyncio.to_thread(lambda: any_speaker.music_library.get_sonos_favorites())

    favs = await _get()

    items = [
        FavoriteItem(
            title=getattr(fav, "title", ""),
            uri=getattr(fav, "reference", {}).get("uri", "") if isinstance(getattr(fav, "reference", None), dict) else str(getattr(fav, "resources", [{}])[0].uri) if getattr(fav, "resources", []) else "",
            meta=getattr(fav, "resource_meta_data", ""),
        )
        for fav in favs
    ]

    return FavoritesResponse(total=len(items), items=items)


@router.post("/{room}/favorite/{name}")
async def play_favorite(room: str, name: str, request: Request):
    """Play a Sonos favorite by name (case-insensitive partial match)."""
    manager = request.app.state.speaker_manager
    speaker = manager.get(room)
    if not speaker:
        return JSONResponse(status_code=404, content={"error": "Room not found", "detail": room})

    @retry_soco()
    async def _get_favs():
        return await asyncio.to_thread(lambda: speaker.music_library.get_sonos_favorites())

    favs = await _get_favs()

    # Find matching favorite (case-insensitive, prefer exact match, then prefix, then contains)
    name_lower = name.lower()
    exact = None
    prefix = None
    contains = None
    for fav in favs:
        title = getattr(fav, "title", "")
        title_lower = title.lower()
        if title_lower == name_lower:
            exact = fav
            break
        elif prefix is None and title_lower.startswith(name_lower):
            prefix = fav
        elif contains is None and name_lower in title_lower:
            contains = fav

    match = exact or prefix or contains
    if not match:
        available = [getattr(f, "title", "") for f in favs]
        return JSONResponse(
            status_code=404,
            content={"error": "Favorite not found", "detail": f"'{name}' not found. Available: {available}"},
        )

    @retry_soco()
    async def _play():
        uri = match.resources[0].uri if match.resources else None
        meta = match.resource_meta_data if hasattr(match, "resource_meta_data") else ""
        if uri:
            await asyncio.to_thread(lambda: speaker.play_uri(uri, meta))

    async with manager.get_lock(room):
        await _play()

    return {"status": "ok", "favorite": getattr(match, "title", "")}
