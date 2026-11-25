"""Local privacy preferences and display masking."""
import getpass
import ipaddress
import json
import os
import platform
import re
import shutil
from pathlib import Path

APPDATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))
SETTINGS = APPDATA / 'RaksToolKit' / 'settings.json'
LEGACY_SETTINGS = APPDATA / 'WinToolKit' / 'settings.json'


def migrate_settings():
    """Copy legacy preferences without overwriting newer settings."""
    if SETTINGS.exists() or not LEGACY_SETTINGS.is_file():
        return
    try:
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        if not SETTINGS.exists():
            shutil.copy2(LEGACY_SETTINGS, SETTINGS)
    except OSError:
        pass


def load_privacy():
    migrate_settings()
    try:
        return json.loads(SETTINGS.read_text(encoding='utf-8')).get('privacy_mode') is True
    except (OSError, ValueError, TypeError):
        return False


def save_privacy(value):
    migrate_settings()
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS.with_suffix('.tmp')
    tmp.write_text(json.dumps({'privacy_mode': bool(value)}, indent=2), encoding='utf-8')
    tmp.replace(SETTINGS)


def redact(value, enabled):
    text = str(value)
    if not enabled:
        return text
    names = {platform.node(), os.getenv('COMPUTERNAME', ''), getpass.getuser(), os.getenv('USERNAME', '')}
    for name in sorted(filter(None, names), key=len, reverse=True):
        text = re.sub(re.escape(name), '[hidden]', text, flags=re.IGNORECASE)

    def mask(match):
        try:
            ipaddress.ip_address(match.group())
            return '[IP hidden]'
        except ValueError:
            return match.group()

    return re.sub(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])', mask, text)
