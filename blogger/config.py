"""
Configuration module for the Blogger Agent.
Loads settings from environment variables and provides defaults.
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent / ".env")


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # LLM Configuration
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    model_name: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "gemma-4-26b-a4b-it"))

    # Scraping Configuration
    scraping_mode: str = field(default_factory=lambda: os.getenv("SCRAPING_MODE", "live"))

    # Content Configuration
    num_articles: int = field(default_factory=lambda: int(os.getenv("NUM_ARTICLES", "3")))

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # Paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent)

    @property
    def articles_dir(self) -> Path:
        # Route generated articles directly to the Jekyll root _posts directory
        return self.project_root.parent / "_posts"

    @property
    def raw_data_dir(self) -> Path:
        return self.project_root / "storage" / "data" / "raw"

    @property
    def memory_dir(self) -> Path:
        return self.project_root / "memory"

    @property
    def memory_file(self) -> Path:
        return self.memory_dir / "topics.json"

    def validate(self) -> None:
        """Validate required settings."""
        if not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is required. "
                "Get one at https://aistudio.google.com/apikey "
                "and set it in your .env file."
            )

        if self.scraping_mode not in ("live", "mock"):
            raise ValueError(f"SCRAPING_MODE must be 'live' or 'mock', got '{self.scraping_mode}'")

        if self.num_articles < 1:
            raise ValueError(f"NUM_ARTICLES must be >= 1, got {self.num_articles}")

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_settings(**overrides) -> Settings:
    """Create and validate settings, applying any CLI overrides."""
    settings = Settings()

    # Apply overrides from CLI arguments
    for key, value in overrides.items():
        if value is not None and hasattr(settings, key):
            setattr(settings, key, value)

    settings.validate()
    settings.ensure_directories()
    setup_logging(settings.log_level)

    return settings
