"""Enhanced configuration management with validation and environment support."""
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    supabase_url: str = Field(..., env="SUPABASE_URL", description="Supabase project URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY", description="Supabase anon key")
    supabase_service_role_key: Optional[str] = Field(default=None, env="SUPABASE_SERVICE_ROLE_KEY", description="Supabase service role key")
    max_connections: int = Field(default=10, env="DB_MAX_CONNECTIONS", ge=1, le=100, description="Maximum database connections")
    timeout: int = Field(default=30, env="DB_TIMEOUT", ge=5, le=300, description="Database timeout in seconds")
    enable_rls: bool = Field(default=True, env="ENABLE_RLS", description="Enable Row Level Security")
    vector_dimension: int = Field(default=768, env="VECTOR_DIMENSION", description="Vector embedding dimension")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD", description="Vector similarity threshold")


class AuthSettings(BaseSettings):
    """Authentication and security settings."""
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_secret_key: Optional[str] = Field(None, env="JWT_SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE", ge=5)
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE", ge=1)
    password_reset_expire_minutes: int = Field(default=15, env="PASSWORD_RESET_EXPIRE", ge=5)
    
    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v, values):
        if not v and values.get('environment') == 'production':
            raise ValueError('JWT_SECRET_KEY is required in production')
        return v


class ModelSettings(BaseSettings):
    """AI model configuration settings."""
    chat_model: str = Field(default="gemini/gemini-2.0-flash", env="MODEL_CHAT")
    light_model: str = Field(default="gemini/gemini-2.0-flash-lite", env="MODEL_LIGHT")
    embedding_model: str = Field(default="text-embedding-ada-002", env="MODEL_EMBEDDING")
    
    # Temperature settings
    temperature_chat: float = Field(default=0.2, env="TEMP_CHAT", ge=0.0, le=2.0)
    temperature_classifiers: float = Field(default=0.0, env="TEMP_CLASSIFIERS", ge=0.0, le=1.0)
    
    # Token limits
    max_tokens_chat: int = Field(default=1000, env="MAX_TOKENS_CHAT", ge=100, le=4000)
    max_tokens_summary: int = Field(default=500, env="MAX_TOKENS_SUMMARY", ge=50, le=2000)
    
    # API keys
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")


class SecuritySettings(BaseSettings):
    """Security and safety configuration."""
    enable_input_moderation: bool = Field(default=True, env="ENABLE_INPUT_MODERATION")
    enable_output_moderation: bool = Field(default=True, env="ENABLE_OUTPUT_MODERATION")
    enable_pii_detection: bool = Field(default=True, env="ENABLE_PII_DETECTION")
    enable_crisis_detection: bool = Field(default=True, env="ENABLE_CRISIS_DETECTION")
    enable_crisis_escalation: bool = Field(default=False, env="ENABLE_CRISIS_ESCALATION")
    
    # Rate limiting
    rate_limit_ws_per_min: int = Field(default=60, env="RATE_LIMIT_WS", ge=1, le=1000)
    rate_limit_api_per_min: int = Field(default=100, env="RATE_LIMIT_API", ge=1, le=1000)
    
    # Content filtering thresholds
    pii_confidence_threshold: float = Field(default=0.8, env="PII_THRESHOLD", ge=0.0, le=1.0)
    crisis_confidence_threshold: float = Field(default=0.7, env="CRISIS_THRESHOLD", ge=0.0, le=1.0)


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    level: str = Field(default="INFO", env="LOG_LEVEL")
    log_to_file: bool = Field(default=True, env="LOG_TO_FILE")
    log_dir: str = Field(default="logs", env="LOG_DIR")
    structured_logging: bool = Field(default=True, env="STRUCTURED_LOGGING")
    include_trace: bool = Field(default=False, env="LOG_INCLUDE_TRACE")
    
    @validator('level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()


class Settings(BaseSettings):
    """Main application settings."""
    # Core application settings
    app_name: str = Field(default="AI Therapist API", env="APP_NAME")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT", ge=1, le=65535)
    reload: bool = Field(default=True, env="RELOAD")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    models: ModelSettings = Field(default_factory=ModelSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    # Feature flags
    enable_websocket: bool = Field(default=True, env="ENABLE_WEBSOCKET")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    enable_health_checks: bool = Field(default=True, env="ENABLE_HEALTH_CHECKS")
    
    @validator('environment')
    def validate_environment(cls, v):
        valid_envs = ['development', 'staging', 'production', 'testing']
        if v not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v
    
    # @validator('cors_origins', pre=True)
    # def parse_cors_origins(cls, v):
    #     if isinstance(v, str):
    #         return [origin.strip() for origin in v.split(',') if origin.strip()]
    #     return v
    
    # @model_validator(mode="before")
    # def validate_production_settings(cls, values):
    #     environment = values.get('environment')
    #     if environment == 'production':
    #         # if values.get('debug', True):
    #         #     raise ValueError('Debug mode must be disabled in production')
    #         if not values.get('database', {}).get('url'):
    #             raise ValueError('Database URL is required in production')
    #     return values
    
    @property
    def is_development(self) -> bool:
        return self.environment == 'development'
    
    @property
    def is_production(self) -> bool:
        return self.environment == 'production'
    
    @property
    def is_testing(self) -> bool:
        return self.environment == 'testing'
    
    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        validate_assignment=True,
        extra="ignore",  # Ignore unrelated env vars at the top level
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def get_environment_file() -> Optional[Path]:
    """Get the appropriate environment file based on current environment."""
    env = get_settings().environment
    env_files = {
        'development': '.env.dev',
        'staging': '.env.staging', 
        'production': '.env.prod',
        'testing': '.env.test'
    }
    
    env_file = Path(env_files.get(env, '.env'))
    return env_file if env_file.exists() else None
