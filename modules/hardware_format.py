"""Pure display formatting for hardware snapshots; never queries hardware."""
import math


def _valid(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and value >= 0 and (isinstance(value, int) or math.isfinite(value)))


def format_bytes(value):
    if not _valid(value):
        return 'N/A'
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'):
        if value < 1024 or unit == 'PiB':
            return f'{value:.0f} B' if unit == 'B' else f'{value:.2f} {unit}'
        value /= 1024


def format_frequency(value):
    if not _valid(value):
        return 'N/A'
    return f'{value / 1000:.2f} GHz' if value >= 1000 else f'{value:.0f} MHz'


def format_percent(value):
    return f'{value:.1f}%' if _valid(value) and value <= 100 else 'N/A'


def format_count(value):
    return str(int(value)) if _valid(value) and int(value) == value else 'N/A'


def format_text(value):
    return value.strip() if isinstance(value, str) and value.strip() else 'N/A'


def format_system(snapshot):
    """Return display strings without changing the raw snapshot."""
    fields = {'cpu_name': format_text, 'os_name': format_text,
              'physical_cores': format_count, 'logical_cores': format_count,
              'cpu_percent': format_percent, 'cpu_frequency_mhz': format_frequency,
              'memory_total_bytes': format_bytes, 'memory_available_bytes': format_bytes,
              'memory_percent': format_percent}
    return {key: formatter(snapshot.get(key)) for key, formatter in fields.items()}


def format_volume(snapshot):
    fields = {'device': format_text, 'mountpoint': format_text, 'filesystem': format_text,
              'total_bytes': format_bytes, 'free_bytes': format_bytes,
              'used_bytes': format_bytes, 'percent': format_percent}
    return {key: formatter(snapshot.get(key)) for key, formatter in fields.items()}
