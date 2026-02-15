# Sonos API

A stable Python HTTP API for controlling Sonos speakers. Built as a replacement for `node-sonos-http-api` — designed to run reliably on a Raspberry Pi.

## Why

The Node.js alternative crashes frequently and is painful to maintain. This project uses FastAPI + SoCo for a clean, async REST API with automatic discovery and structured error handling.

## Quick Start

```bash
# Clone and install
git clone https://github.com/youruser/sonos-api.git
cd sonos-api
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Run
uvicorn sonos_api.main:app --host 0.0.0.0 --port 5005
```

Open http://localhost:5005/docs for interactive API docs.

## Configuration

Set via environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `SONOS_API_HOST` | `0.0.0.0` | Bind address |
| `SONOS_API_PORT` | `5005` | Port |
| `SONOS_DISCOVERY_INTERVAL` | `30` | Speaker discovery interval (seconds) |
| `SONOS_LOG_LEVEL` | `INFO` | Log level |
| `SONOS_LOG_JSON` | `false` | JSON log output |
| `SONOS_TTS_CACHE_DIR` | `static` | TTS audio cache directory |

See `.env.example` for a template.

## API

All responses are JSON. Room names in URLs are case-insensitive with spaces replaced by underscores (e.g. `Living Room` → `living_room`).

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check + speaker count |
| `GET` | `/zones` | All groups/zones topology |
| `POST` | `/pauseall` | Pause all playing zones |
| `POST` | `/resumeall` | Resume all paused zones |
| `GET` | `/events` | SSE event stream |

### Playback

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/{room}/state` | Current track, volume, transport state |
| `POST` | `/{room}/play` | Resume playback |
| `POST` | `/{room}/pause` | Pause playback |
| `POST` | `/{room}/playpause` | Toggle play/pause |
| `POST` | `/{room}/next` | Next track |
| `POST` | `/{room}/previous` | Previous track |
| `POST` | `/{room}/seek` | Seek: `{"position": 120}` or `{"track": 3}` |

### Volume

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `PUT` | `/{room}/volume` | `{"volume": 25}` or `{"volume": "+5"}` | Set volume |
| `POST` | `/{room}/mute` | — | Mute |
| `POST` | `/{room}/unmute` | — | Unmute |
| `POST` | `/{room}/togglemute` | — | Toggle mute |

### Queue & Favorites

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/{room}/queue` | Get queue |
| `DELETE` | `/{room}/queue` | Clear queue |
| `GET` | `/favorites` | List Sonos favorites |
| `POST` | `/{room}/favorite/{name}` | Play a favorite (fuzzy name match) |

### Groups

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/{room}/join/{other}` | Join room to other's group |
| `POST` | `/{room}/leave` | Leave current group |
| `PUT` | `/{room}/groupvolume` | Set group volume |

### Settings

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `PUT` | `/{room}/playmode` | `{"shuffle": true, "repeat": "all"}` | Set play mode |
| `PUT` | `/{room}/sleep` | `{"seconds": 600}` | Sleep timer (0 to cancel) |
| `PUT` | `/{room}/equalizer` | `{"bass": 5, "treble": -2}` | Set EQ (-10 to 10) |

### TTS

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `POST` | `/{room}/say` | `{"text": "Hello", "language": "en", "volume": 40}` | Text-to-speech announcement |

## Examples

```bash
# Check what's available
curl localhost:5005/zones

# Control playback
curl -X POST localhost:5005/living_room/pause
curl -X POST localhost:5005/living_room/play

# Set volume
curl -X PUT localhost:5005/living_room/volume -H 'Content-Type: application/json' -d '{"volume": 20}'

# Play a favorite
curl -X POST localhost:5005/living_room/favorite/chill

# Group speakers
curl -X POST localhost:5005/kitchen/join/living_room

# TTS announcement
curl -X POST localhost:5005/living_room/say -H 'Content-Type: application/json' -d '{"text": "Dinner is ready", "volume": 40}'

# Pause everything
curl -X POST localhost:5005/pauseall
```

## Raspberry Pi Deployment

```bash
sudo ./deploy/install.sh
```

This sets up a systemd service with auto-restart, watchdog, and memory limits. See `deploy/sonos-api.service` for details.

```bash
# Manage the service
sudo systemctl status sonos-api
sudo journalctl -u sonos-api -f
```

## Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — async web framework with auto-generated OpenAPI docs
- **[SoCo](https://github.com/SoCo/SoCo)** — Python library for Sonos (UPnP/SSDP discovery + SOAP control)
- **[gTTS](https://github.com/pndurette/gTTS)** — Google Text-to-Speech
- **[structlog](https://www.structlog.org/)** — structured logging
- **[pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)** — typed configuration

## License

MIT
