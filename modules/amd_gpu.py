"""Read-only AMD GPU metrics through the amd-adlx bindings.

Each sample creates an ADLXHelper, initializes it, reads one GPU, then releases
every ADLX interface before Terminate. Interface objects are not constructed
directly: GetSystemServices returns None until initialization succeeds.
"""

def _import_adlx():
    from adlx import ADLX
    return ADLX


def _call(obj, name):
    try:
        return getattr(obj, name)()
    except Exception:
        return None


def _supported(support, name):
    """Missing support data means the metric may still be readable."""
    if support is None:
        return True
    return bool(_call(support, name))


def _quantity(value, unit):
    if value is None or isinstance(value, bool):
        return 'Unavailable'
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 'Unavailable'
    if unit == '%':
        return f'{number:g}%'
    return f'{number:g} {unit}'


def _select_gpu(gpus, discrete_type):
    chosen = None
    for gpu in gpus:
        if chosen is None:
            chosen = gpu
        if _call(gpu, 'Type') == discrete_type:
            return gpu
    return chosen


def _vram(gpu, metrics, support):
    if not _supported(support, 'IsSupportedGPUVRAM'):
        return 'Unavailable'
    used = _call(metrics, 'GPUVRAM')
    total = _call(gpu, 'TotalVRAM')
    try:
        used_mb = float(used)
        total_mb = float(total)
    except (TypeError, ValueError):
        return 'Unavailable'
    if total_mb <= 0:
        return 'Unavailable'
    # ADLX reports megabytes. The Gaming page parses the NVIDIA "used / total MiB" text.
    return f'{used_mb:g} / {total_mb:g} MiB'


def _power(metrics, support):
    if _supported(support, 'IsSupportedGPUPower'):
        value = _quantity(_call(metrics, 'GPUPower'), 'W')
        if value != 'Unavailable':
            return value
    if _supported(support, 'IsSupportedGPUTotalBoardPower'):
        return _quantity(_call(metrics, 'GPUTotalBoardPower'), 'W')
    return 'Unavailable'


def _apply_metrics(info, gpu, metrics, support):
    if _supported(support, 'IsSupportedGPUUsage'):
        info['utilization'] = _quantity(_call(metrics, 'GPUUsage'), '%')
    if _supported(support, 'IsSupportedGPUTemperature'):
        info['temperature'] = _quantity(_call(metrics, 'GPUTemperature'), '°C')
    info['vram'] = _vram(gpu, metrics, support)
    if _supported(support, 'IsSupportedGPUClockSpeed'):
        info['core_clock'] = _quantity(_call(metrics, 'GPUClockSpeed'), 'MHz')
    if _supported(support, 'IsSupportedGPUVRAMClockSpeed'):
        info['memory_clock'] = _quantity(_call(metrics, 'GPUVRAMClockSpeed'), 'MHz')
    info['power'] = _power(metrics, support)


def read_amd_metrics():
    """Return normalized GPU metrics, or None when ADLX cannot be queried."""
    helper = None
    system = None
    monitoring = None
    gpus = None
    gpu = None
    support = None
    metrics = None
    try:
        try:
            adlx = _import_adlx()
        except (ImportError, OSError):
            return None
        helper = adlx.ADLXHelper()
        result = helper.Initialize()
        success = (
            result == adlx.ADLX_RESULT.ADLX_OK
            or result == adlx.ADLX_RESULT.ADLX_ALREADY_INITIALIZED
        )
        if not success:
            return None
        system = helper.GetSystemServices()
        if system is None:
            return None
        listed = system.GetGPUs() or []
        gpus = list(listed)
        if not gpus:
            return None
        gpu = _select_gpu(gpus, adlx.ADLX_GPU_TYPE.GPUTYPE_DISCRETE)
        if gpu is None:
            return None
        info = {
            'name': 'Unavailable',
            'vendor': 'AMD',
            'utilization': 'Unavailable',
            'temperature': 'Unavailable',
            'vram': 'Unavailable',
            'core_clock': 'Unavailable',
            'memory_clock': 'Unavailable',
            'power': 'Unavailable',
        }
        name = _call(gpu, 'Name')
        if isinstance(name, str) and name.strip():
            info['name'] = name.strip()
        monitoring = _call(system, 'GetPerformanceMonitoringServices')
        if monitoring is not None:
            try:
                support = monitoring.GetSupportedGPUMetrics(gpu)
            except Exception:
                support = None
            try:
                metrics = monitoring.GetCurrentGPUMetrics(gpu)
            except Exception:
                metrics = None
            if metrics is not None:
                _apply_metrics(info, gpu, metrics, support)
        return info
    except Exception:
        return None
    finally:
        system = monitoring = gpus = gpu = support = metrics = None
        if helper is not None:
            try:
                helper.Terminate()
            except Exception:
                pass
