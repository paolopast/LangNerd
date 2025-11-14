from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()


class Settings(BaseModel):
    """Centralized application configuration."""

    google_api_key: str = Field(..., description="API key for Gemini / Google Generative AI")
    gemini_model: str = Field(default="gemini-1.5-flash", description="Gemini model used for orchestration")
    serpapi_api_key: str = Field(..., description="API key for SerpAPI (Google Search)")
    default_language: str = Field(default="it", description="Default language for answers")
    search_language: str = Field(default="it", description="Language hint for SerpAPI (hl parameter)")
    search_country: str = Field(default="it", description="Country hint for SerpAPI (gl parameter)")
    search_max_results: int = Field(default=6, description="How many results to fetch per query")
    export_output_dir: str = Field(
        default="generated_guides",
        description="Directory where generated HTML guides are stored",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings; fail fast if required env vars are missing."""

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing GOOGLE_API_KEY environment variable. "
            "Create an API key in Google AI Studio and export it before starting the backend."
        )

    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        raise RuntimeError(
            "Missing SERPAPI_API_KEY environment variable. "
            "Generate one from https://serpapi.com/ and export it before starting the backend."
        )

    export_dir = os.getenv("EXPORT_OUTPUT_DIR", "generated_guides")
    export_dir_path = Path(export_dir)
    if not export_dir_path.is_absolute():
        export_dir_path = (BASE_DIR / export_dir_path).resolve()

    return Settings(
        google_api_key=api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        serpapi_api_key=serpapi_key,
        default_language=os.getenv("DEFAULT_LANGUAGE", "it"),
        search_language=os.getenv("SEARCH_LANGUAGE", "it"),
        search_country=os.getenv("SEARCH_COUNTRY", "it"),
        search_max_results=int(os.getenv("SEARCH_MAX_RESULTS", "6")),
        export_output_dir=str(export_dir_path),
    )
