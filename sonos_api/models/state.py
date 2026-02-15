from pydantic import BaseModel


class TrackInfo(BaseModel):
    title: str = ""
    artist: str = ""
    album: str = ""
    album_art: str = ""
    duration: str = ""
    position: str = ""
    uri: str = ""


class PlayerState(BaseModel):
    room: str
    state: str  # PLAYING, PAUSED_PLAYBACK, STOPPED, TRANSITIONING
    volume: int
    mute: bool
    track: TrackInfo = TrackInfo()


class MemberInfo(BaseModel):
    room: str
    uuid: str


class ZoneInfo(BaseModel):
    coordinator: str
    uuid: str
    members: list[MemberInfo]
    state: str
    volume: int
    track: TrackInfo = TrackInfo()


class HealthResponse(BaseModel):
    status: str = "ok"
    speakers: int = 0


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
