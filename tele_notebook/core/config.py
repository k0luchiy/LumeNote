from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    TELEGRAM_BOT_TOKEN: str
    GOOGLE_API_KEY: str
    REDIS_URL: str
    PIPER_TTS_URL: str
    CHROMA_DB_PATH: str

settings = Settings()