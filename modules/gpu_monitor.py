"""GPU monitoring with optional vendor-specific backends."""
import csv
import json
import shutil
import subprocess

NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
NVIDIA_FIELDS = ('name', 'utilization.gpu', 'temperature.gpu', 'memory.used',
                 'memory.total', 'clocks.gr', 'clocks.mem', 'power.draw')
METRIC_KEYS = ('name', 'vendor', 'utilization', 'temperature', 'vram',
               'core_clock', 'memory_clock', 'power')


def blank_gpu_info(name='Unavailable', vendor='Unknown'):
    """Normalized metrics shared by the NVIDIA and AMD providers."""
    info = {key: 'Unavailable' for key in METRIC_KEYS}
    info['name'] = name
    info['vendor'] = vendor
    return info


def _value(raw, unit):
    raw = raw.strip()
    if not raw or raw.upper() in ('N/A', '[NOT SUPPORTED]', 'NOT SUPPORTED'):
        return 'Unavailable'
    try:
        number = float(raw)
    except ValueError:
        return 'Unavailable'
    return f'{number:g} {unit}'


def _adapter_names():
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
             'Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress'],
            capture_output=True, text=True, errors='replace', timeout=12,
            creationflags=NO_WINDOW)
        if result.returncode == 0 and result.stdout.strip():
            names = json.loads(result.stdout.strip())
            return [names] if isinstance(names, str) else [str(n) for n in names if n]
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        pass
    return []


def _vendor(names):
    lower_names = ' '.join(names).lower()
    if 'nvidia' in lower_names or 'geforce' in lower_names:
        return 'NVIDIA'
    if 'amd' in lower_names or 'radeon' in lower_names:
        return 'AMD'
    if 'intel' in lower_names:
        return 'Intel'
    return 'Unknown'


def _fill_nvidia(info):
    executable = shutil.which('nvidia-smi')
    if not executable:
        return info
    try:
        result = subprocess.run(
            [executable, '--query-gpu=' + ','.join(NVIDIA_FIELDS),
             '--format=csv,noheader,nounits'], capture_output=True, text=True,
            errors='replace', timeout=6, creationflags=NO_WINDOW)
        if result.returncode != 0 or not result.stdout.strip():
            return info
        fields = next(csv.reader(result.stdout.splitlines()))
        if len(fields) != len(NVIDIA_FIELDS):
            return info
        name, utilization, temp, used, total, core, mem, power = [x.strip() for x in fields]
        info['name'] = name or info['name']
        info['vendor'] = 'NVIDIA'
        info['utilization'] = _value(utilization, '%').replace(' %', '%')
        info['temperature'] = _value(temp, '°C')
        if _value(used, 'MiB') != 'Unavailable' and _value(total, 'MiB') != 'Unavailable':
            info['vram'] = f'{float(used):g} / {float(total):g} MiB'
        info['core_clock'] = _value(core, 'MHz')
        info['memory_clock'] = _value(mem, 'MHz')
        info['power'] = _value(power, 'W')
    except (OSError, subprocess.TimeoutExpired, ValueError, StopIteration, csv.Error):
        pass
    return info


def _fill_amd(info):
    from modules.amd_gpu import read_amd_metrics
    try:
        amd = read_amd_metrics()
    except Exception:
        return info
    if not isinstance(amd, dict):
        return info
    fallback_name = info['name']
    for key in METRIC_KEYS:
        value = amd.get(key)
        if value not in (None, ''):
            info[key] = value
    info['vendor'] = 'AMD'
    if info['name'] in (None, '', 'Unavailable'):
        info['name'] = fallback_name
    return info


def gpu_info():
    """Return display-ready GPU metrics; never require a vendor utility."""
    names = _adapter_names()
    info = blank_gpu_info(', '.join(names) or 'Unavailable', _vendor(names))
    if info['vendor'] == 'NVIDIA':
        return _fill_nvidia(info)
    if info['vendor'] == 'AMD':
        return _fill_amd(info)
    return info
