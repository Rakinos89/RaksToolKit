"""Accent preferences, stored alongside existing privacy settings."""
import json
from modules import privacy

ACCENTS = {
    'Green': ('#2BA477', '#20845F'),
    'Blue': ('#3488DB', '#256CB3'),
    'Purple': ('#9461D8', '#774BB3'),
    'Orange': ('#E28B35', '#B96D21'),
    'Red': ('#D85462', '#B33C49'),
}
DEFAULT_ACCENT = 'Green'


def load_accent():
    privacy.migrate_settings()
    try:
        data = json.loads(privacy.SETTINGS.read_text(encoding='utf-8'))
        name = data.get('accent_color') if isinstance(data, dict) else None
        return name if name in ACCENTS else DEFAULT_ACCENT
    except (OSError, ValueError, TypeError):
        return DEFAULT_ACCENT


def save_accent(name):
    if name not in ACCENTS:
        raise ValueError('Unknown accent color')
    privacy.migrate_settings()
    data = privacy.read_settings()
    data['accent_color'] = name
    privacy.write_settings(data)
