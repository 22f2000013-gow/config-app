"""
12-Factor Config Precedence FastAPI Service
Layers (low → high priority):
  1. Hardcoded defaults
  2. config.<ENV>.yaml
  3. .env file
  4. OS environment variables (APP_* prefix)
  5. ?set=key=value query params (highest)
"""

import os
import yaml
from pathlib import Path
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# ── App setup ──────────────────────────────────────────────────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://exam.sanand.workers.dev"],  # grader origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Layer 1: Hardcoded defaults ────────────────────────────────────────────
DEFAULTS = {
    "port": 8000,
    "workers": 2,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret",
}

# ── Helpers ─────────────────────────────────────────────────────────────────

def coerce(key: str, value) -> object:
    """Convert a raw string value to the correct Python type for the key."""
    if key == "port" or key == "workers":
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes", "on")
    return str(value)   # log_level, api_key, and anything else → str


def normalize_key(raw_key: str) -> str | None:
    """
    Map raw config keys (from any layer) to canonical keys.
    Only NUM_WORKERS is aliased; unknown keys are passed through.
    """
    k = raw_key.strip().upper()
    if k == "NUM_WORKERS":
        return "workers"
    # Map APP_PORT → port, APP_DEBUG → debug, etc.
    mapping = {
        "PORT": "port",
        "WORKERS": "workers",
        "DEBUG": "debug",
        "LOG_LEVEL": "log_level",
        "API_KEY": "api_key",
    }
    return mapping.get(k, raw_key.lower())


def load_yaml_layer(env: str) -> dict:
    """Load config.<env>.yaml from the same directory as this file."""
    base = Path(__file__).parent
    yaml_path = base / f"config.{env}.yaml"
    if not yaml_path.exists():
        return {}
    with open(yaml_path) as f:
        data = yaml.safe_load(f) or {}
    # Keys in YAML are already canonical (port, workers, …)
    return {k.lower(): v for k, v in data.items()}


def load_dotenv_layer() -> dict:
    """Read .env file (does NOT pollute os.environ)."""
    base = Path(__file__).parent
    env_path = base / ".env"
    raw = dotenv_values(env_path)
    result = {}
    for raw_key, raw_val in raw.items():
        canon = normalize_key(raw_key)
        if canon:
            result[canon] = raw_val
    return result


def load_os_env_layer() -> dict:
    """Read OS environment variables that start with APP_ (strip the prefix)."""
    result = {}
    for raw_key, raw_val in os.environ.items():
        if raw_key.upper().startswith("APP_"):
            short = raw_key[4:]          # strip 'APP_'
            canon = normalize_key(short)
            if canon:
                result[canon] = raw_val
    return result


# ── Endpoint ────────────────────────────────────────────────────────────────

@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):
    """
    Merge all config layers and return the effective config.
    ?set=key=value overrides take the highest precedence.
    """
    env = os.environ.get("APP_ENV", "production")

    # Build merged dict — later layers overwrite earlier ones
    merged: dict = dict(DEFAULTS)                # layer 1: defaults

    for k, v in load_yaml_layer(env).items():    # layer 2: YAML
        merged[k] = v

    for k, v in load_dotenv_layer().items():     # layer 3: .env
        merged[k] = v

    for k, v in load_os_env_layer().items():     # layer 4: OS env (APP_*)
        merged[k] = v

    # Layer 5: CLI overrides from query params (?set=key=value)
    for item in set:
        if "=" in item:
            k, _, v = item.partition("=")
            merged[k.strip().lower()] = v.strip()

    # Coerce all values to the correct type
    result = {k: coerce(k, v) for k, v in merged.items()}

    # Secret masking — api_key must NEVER be exposed
    result["api_key"] = "****"

    # Ensure the five required keys are present
    for key in ("port", "workers", "debug", "log_level", "api_key"):
        if key not in result:
            result[key] = coerce(key, DEFAULTS[key])

    return result
