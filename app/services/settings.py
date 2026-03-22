"""App settings — in-memory + JSON persistence."""
import json
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))
SETTINGS_FILE = DATA_DIR / "settings.json"

_defaults = {
    "prowlarr_url": os.environ.get("PROWLARR_URL", "http://prowlarr:9696"),
    "prowlarr_api_key": os.environ.get("PROWLARR_API_KEY", ""),
    "qbit_url": os.environ.get("QBIT_URL", "http://qbittorrent:8081"),
    "qbit_user": os.environ.get("QBIT_USER", "admin"),
    "qbit_pass": os.environ.get("QBIT_PASS", "adminadmin"),
    "abs_url": os.environ.get("ABS_URL", "http://audiobookshelf:80"),
    "abs_user": os.environ.get("ABS_USER", ""),
    "abs_pass": os.environ.get("ABS_PASS", ""),
    "qbit_save_path": os.environ.get("QBIT_SAVE_PATH", ""),
    "audiobook_dir": os.environ.get("AUDIOBOOK_DIR", "/audiobooks"),
}

_settings: dict = {}


def _load():
    global _settings
    _settings = dict(_defaults)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text())
            _settings.update(saved)
        except Exception:
            pass


def _save():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(_settings, indent=2))


def get_all() -> dict:
    """Return all settings. Mask passwords as booleans."""
    if not _settings:
        _load()
    out = dict(_settings)
    for k in ("prowlarr_api_key", "qbit_pass", "abs_pass"):
        out[k] = bool(out.get(k))
    return out


def get_public() -> dict:
    """Return non-sensitive settings for regular users."""
    if not _settings:
        _load()
    return {
        "prowlarr_connected": bool(_settings.get("prowlarr_api_key")),
        "qbit_connected": bool(_settings.get("qbit_url")),
        "abs_connected": bool(_settings.get("abs_url") and _settings.get("abs_user")),
    }


def get(key: str, default=None):
    if not _settings:
        _load()
    return _settings.get(key, default)


def update(data: dict) -> dict:
    """Update settings and apply to running config."""
    if not _settings:
        _load()
    for k, v in data.items():
        if v is not None and k in _defaults:
            _settings[k] = v
    _save()
    # Apply to running config modules
    _apply()
    return get_all()


def _apply():
    """Push updated settings to config module and service modules."""
    import app.config as cfg
    cfg.PROWLARR_URL = _settings.get("prowlarr_url", cfg.PROWLARR_URL)
    cfg.PROWLARR_API_KEY = _settings.get("prowlarr_api_key", cfg.PROWLARR_API_KEY)
    cfg.QBIT_URL = _settings.get("qbit_url", cfg.QBIT_URL)
    cfg.QBIT_USER = _settings.get("qbit_user", cfg.QBIT_USER)
    cfg.QBIT_PASS = _settings.get("qbit_pass", cfg.QBIT_PASS)
    cfg.ABS_URL = _settings.get("abs_url", cfg.ABS_URL)
    cfg.ABS_USER = _settings.get("abs_user", cfg.ABS_USER)
    cfg.ABS_PASS = _settings.get("abs_pass", cfg.ABS_PASS)
    cfg.QBIT_SAVE_PATH = _settings.get("qbit_save_path", cfg.QBIT_SAVE_PATH)
    cfg.AUDIOBOOK_DIR = _settings.get("audiobook_dir", cfg.AUDIOBOOK_DIR)


_load()
