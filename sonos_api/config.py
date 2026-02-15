from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "SONOS_"}

    api_host: str = "0.0.0.0"
    api_port: int = 5005
    discovery_interval: int = 30
    log_level: str = "INFO"
    log_json: bool = False
    tts_cache_dir: str = "static"


settings = Settings()
