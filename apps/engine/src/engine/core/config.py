"""Runtime configuration for Semantic Web KMS."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application runtime settings loaded from environment variables or .env file.

    Attributes:
        AGRAPH_CLOUD_URL (str): AllegroGraph cloud repository URL.
        AGRAPH_USERNAME (str): AllegroGraph username.
        AGRAPH_PASSWORD (str): AllegroGraph password.
        AGRAPH_USE_SSL (bool): Whether to use SSL for AllegroGraph connections.
        AGRAPH_SERVER_URL (str): AllegroGraph server URL.
        AGRAPH_REPO (str): AllegroGraph repository name.
        API_HOST (str): Host for backend API server.
        API_PORT (int): Port for backend API server.
        API_DEBUG (bool): Debug mode for backend API server.
        GEMINI_API_KEY (str): API key for Gemini LLM integration.

    Pydantic will still raise a validation error at runtime if required fields
    are not found in the environment, even though they are marked as optional here
    for the static type checker.
    """

    # AllegroGraph API configuration
    # These are required at runtime. They are marked optional here to satisfy
    # static analysis tools like Pyright.
    AGRAPH_CLOUD_URL: str | None = Field(
        default=None, validation_alias="AGRAPH_CLOUD_URL"
    )
    AGRAPH_USERNAME: str | None = Field(
        default=None, validation_alias="AGRAPH_USERNAME"
    )
    AGRAPH_PASSWORD: str | None = Field(
        default=None, validation_alias="AGRAPH_PASSWORD"
    )
    AGRAPH_SERVER_URL: str | None = Field(
        default=None, validation_alias="AGRAPH_SERVER_URL"
    )
    AGRAPH_REPO: str | None = Field(default=None, validation_alias="AGRAPH_REPO")

    # Use SSL by default
    AGRAPH_USE_SSL: bool = Field(default=True, validation_alias="AGRAPH_USE_SSL")

    # Backend configuration with sensible defaults
    API_HOST: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    API_PORT: int = Field(default=8000, validation_alias="API_PORT")
    API_DEBUG: bool = Field(default=False, validation_alias="API_DEBUG")

    # LLM API Keys
    GEMINI_API_KEY: str = Field(default="", validation_alias="GEMINI_API_KEY")

    # Output directory base
    OUTPUT_DIR_BASE: str = Field(default="output", validation_alias="KMS_OUTPUT_DIR")

    class Config:
        """Configuration for environment variables and settings."""

        env_file = ".env"
        case_sensitive = False


settings = Settings()

# Runtime check to ensure settings are loaded
if not all([
    settings.AGRAPH_CLOUD_URL,
    settings.AGRAPH_USERNAME,
    settings.AGRAPH_PASSWORD,
    settings.AGRAPH_SERVER_URL,
    settings.AGRAPH_REPO,
]):
    raise RuntimeError("Credentials not found in environment.")
