"""
Shared structured configuration for the paper-reading assistant.

The checked-in config stores provider-neutral settings and environment-variable
names. Secret values still live only in the runtime environment.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "paper-reading-assistant" / "config.json"

DEFAULT_CONFIG = {
    "selection": {
        "defaults": {
            "recency_days": 730,
            "min_year": 2020,
            "max_results_to_score": 50,
            "curated_sources": [],
            "curated_max_weeks": 8,
        },
        "score_weights": {
            "relevance": 35.0,
            "citation_signal": 17.0,
            "recency_trend": 18.0,
            "curated_popularity": 10.0,
            "source_credibility": 8.0,
            "accessibility": 7.0,
            "novelty_diversity": 5.0,
        },
    },
    "sources": {
        "openalex_works_url": "https://api.openalex.org/works",
        "dair_readme_url": "https://raw.githubusercontent.com/dair-ai/AI-Papers-of-the-Week/main/README.md",
        "dair_raw_base": "https://raw.githubusercontent.com/dair-ai/AI-Papers-of-the-Week/main",
        "curated_source_labels": {
            "dair-ai-weekly": "DAIR AI Papers of the Week",
        },
    },
    "rendering": {
        "default_output_name": "report.html",
    },
    "email": {
        "provider": "gmail",
        "providers": {
            "gmail": {
                "host": "smtp.gmail.com",
                "port": 587,
                "username_placeholder": "your-gmail-address@gmail.com",
                "password_placeholder": "your-google-app-password",
                "email_from_placeholder": "your-gmail-address@gmail.com",
                "email_to_placeholder": "your-delivery-email@example.com",
                "starttls_ports": [587],
            },
        },
        "smtp": {
            "host_env": "REPORT_SMTP_HOST",
            "port_env": "REPORT_SMTP_PORT",
            "default_port": 587,
            "username_env": "REPORT_SMTP_USERNAME",
            "password_env": "REPORT_SMTP_PASSWORD",
            "from_env": "REPORT_EMAIL_FROM",
            "starttls_ports": [587],
        },
    },
}


def deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_app_config(path: Path | str | None = None) -> dict:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        if path:
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return copy.deepcopy(DEFAULT_CONFIG)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a JSON object: {config_path}")
    return deep_merge(DEFAULT_CONFIG, data)


def selection_defaults(config: dict) -> dict:
    return (config.get("selection") or {}).get("defaults") or {}


def score_weights(config: dict) -> dict:
    weights = (config.get("selection") or {}).get("score_weights") or {}
    return {key: float(value) for key, value in weights.items()}


def source_settings(config: dict) -> dict:
    return config.get("sources") or {}


def email_smtp_settings(config: dict) -> dict:
    return ((config.get("email") or {}).get("smtp") or {})
