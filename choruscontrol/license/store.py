"""Persist uploaded license key on disk (offline; no phone-home)."""

from __future__ import annotations

from pathlib import Path

from choruscontrol.config import Settings


def license_file_path(settings: Settings) -> Path:
    return Path(settings.sqlite_path).resolve().parent / "license.key"


def load_stored_license(settings: Settings) -> str | None:
    path = license_file_path(settings)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def save_stored_license(settings: Settings, license_key: str) -> Path:
    path = license_file_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(license_key.strip() + "\n", encoding="utf-8")
    return path


def resolve_license_key(settings: Settings) -> str | None:
    """Precedence: stored file > CHORUSCONTROL_LICENSE_KEY env."""
    stored = load_stored_license(settings)
    if stored:
        return stored
    return settings.license_key
