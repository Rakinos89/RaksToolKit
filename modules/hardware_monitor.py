"""Read-only hardware snapshots. Missing readings are represented by None."""
import math
import psutil
from modules.hardware import cpu_name, windows_name


def _read(call):
    try:
        return call()
    except (OSError, RuntimeError, ValueError, AttributeError, psutil.Error):
        return None


def _number(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isfinite(value) and value >= 0:
            return value
    return None


def system_snapshot():
    """Return numeric readings in bytes, MHz and percent, without UI formatting."""
    memory = _read(psutil.virtual_memory)
    frequency = _read(psutil.cpu_freq)
    return {
        'cpu_name': _read(cpu_name),
        'os_name': _read(windows_name),
        'physical_cores': _number(_read(lambda: psutil.cpu_count(logical=False))),
        'logical_cores': _number(_read(psutil.cpu_count)),
        'cpu_percent': _number(_read(lambda: psutil.cpu_percent(interval=None))),
        'cpu_frequency_mhz': _number(getattr(frequency, 'current', None)),
        'memory_total_bytes': _number(getattr(memory, 'total', None)),
        'memory_available_bytes': _number(getattr(memory, 'available', None)),
        'memory_percent': _number(getattr(memory, 'percent', None)),
    }


def volume_snapshot():
    """Enumerate mounted volumes, retaining entries with unavailable usage."""
    partitions = _read(lambda: psutil.disk_partitions(all=False)) or []
    volumes = []
    for partition in partitions:
        usage = _read(lambda: psutil.disk_usage(partition.mountpoint))
        volumes.append({
            'device': partition.device,
            'mountpoint': partition.mountpoint,
            'filesystem': partition.fstype,
            'total_bytes': _number(getattr(usage, 'total', None)),
            'free_bytes': _number(getattr(usage, 'free', None)),
            'used_bytes': _number(getattr(usage, 'used', None)),
            'percent': _number(getattr(usage, 'percent', None)),
        })
    return volumes
