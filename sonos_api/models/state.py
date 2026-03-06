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


class GroupState(BaseModel):
    volume: int
    mute: bool


class MemberState(BaseModel):
    volume: int
    mute: bool
    playbackState: str
    currentTrack: TrackInfo = TrackInfo()


class MemberInfo(BaseModel):
    uuid: str
    roomName: str
    coordinator: str  # coordinator uuid
    state: MemberState
    groupState: GroupState


class ZoneInfo(BaseModel):
    uuid: str
    coordinator: MemberInfo
    members: list[MemberInfo]


class HealthResponse(BaseModel):
    status: str = "ok"
    speakers: int = 0


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
