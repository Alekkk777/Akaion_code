from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gcp_project: str = "akaion-dev"
    pubsub_topic: str = "workflow-created"
    pubsub_subscription: str = "workflow-created-sub"
    firestore_collection: str = "workflows"
    environment: str = "local"  # local | staging | prod
    log_level: str = "INFO"

    # Feature toggles: default to zero-infra local dev, flip on for staging/prod.
    use_pubsub: bool = False
    use_firestore: bool = False

    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
