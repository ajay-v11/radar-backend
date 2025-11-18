from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = ""
    ANTHROPIC_API_KEY: Optional[str] = ""
    GEMINI_API_KEY: Optional[str] = ""
    GROK_API_KEY: Optional[str] = ""
    OPEN_ROUTER_API_KEY: Optional[str] = ""
    FIRECRAWL_API_KEY: Optional[str] = ""
    
    # Application Settings
    APP_NAME: str = "AI Visibility Scoring System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Model Settings - Cost-effective models
    CHATGPT_MODEL: str = "gpt-3.5-turbo"
    INDUSTRY_ANALYSIS_MODEL: str = "gpt-4o-mini"  # For industry detection and analysis
    CLAUDE_MODEL: str = "claude-3-haiku-20240307"  # Cheaper than Sonnet
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"  # Cost-effective Gemini
    GROQ_LLAMA_MODEL: str = "llama-3.1-8b-instant"  # Fast and free on Groq
    OPENROUTER_MISTRAL_MODEL: str = "mistralai/mistral-7b-instruct"  # Cost-effective
    OPENROUTER_QWEN_MODEL: str = "qwen/qwen-2-7b-instruct"  # Cost-effective
    
    # Default models to test (can be overridden by user)
    DEFAULT_MODELS: list = ["chatgpt", "gemini"]
    
    # Query Settings
    NUM_QUERIES: int = 20
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
