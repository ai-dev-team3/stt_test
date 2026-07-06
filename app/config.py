import os

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

    # Google Cloud
    google_application_credentials: str = ""
    gcp_project_id: str = ""
    gcs_bucket: str = ""

    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-northeast-2"
    aws_s3_bucket: str = ""

    database_url: str = "sqlite:///stt_test.db"


settings = Settings()

# google SDK는 환경변수로 인증 경로를 읽으므로 .env 값을 승격시킨다
if settings.google_application_credentials:
    os.environ.setdefault(
        "GOOGLE_APPLICATION_CREDENTIALS", settings.google_application_credentials
    )
