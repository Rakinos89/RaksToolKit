"""Append-only local activity history, stored outside the repository."""
from datetime import datetime
from pathlib import Path
import os
import shutil

APPDATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))
LOG_PATH = APPDATA / 'RaksToolKit' / 'activity.log'
LEGACY_LOG_PATH = APPDATA / 'WinToolKit' / 'activity.log'


def migrate_activity():
    """Copy legacy activity history without overwriting newer data."""
    if LOG_PATH.exists() or not LEGACY_LOG_PATH.is_file():
        return
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not LOG_PATH.exists():
            shutil.copy2(LEGACY_LOG_PATH, LOG_PATH)
    except OSError:
        pass


def record(message):
    migrate_activity()
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open('a', encoding='utf-8') as stream:
        stream.write(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n')


def read_recent(limit=400):
    migrate_activity()
    if not LOG_PATH.exists():
        return 'No activity recorded yet.'
    with LOG_PATH.open('r', encoding='utf-8', errors='replace') as stream:
        lines = stream.readlines()
    return ''.join(lines[-limit:]) or 'No activity recorded yet.'
