from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Naver Clova Speech
    clova_invoke_url: str = ""
    clova_secret_key: str = ""

    # Vito (리턴제로)
    vito_client_id: str = ""
    vito_client_secret: str = ""

    # OpenAI Whisper API
    openai_api_key: str = ""

    # SenseVoice-Small은 로컬 모델이라 키 불필요

    database_url: str = "sqlite:///stt_test.db"


settings = Settings()
