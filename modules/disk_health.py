"""Read-only Windows physical disk and reliability monitoring."""
import json
import subprocess
import sys

_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$rows = @(Get-PhysicalDisk | ForEach-Object {
    $disk = $_
    $counter = $null
    $status = 'unavailable'
    try {
        $counter = $disk | Get-StorageReliabilityCounter -ErrorAction Stop
        if ($null -ne $counter) { $status = 'available' }
    } catch {
        if ($_.CategoryInfo.Category -eq 'PermissionDenied') { $status = 'permission_denied' }
    }
    [PSCustomObject]@{
        device_id = [string]$disk.DeviceId
        model = [string]$disk.FriendlyName
        media_type = [string]$disk.MediaType
        bus_type = [string]$disk.BusType
        health_status = [string]$disk.HealthStatus
        operational_status = ($disk.OperationalStatus -join ', ')
        size_bytes = $disk.Size
        reliability_status = $status
        temperature_c = $counter.Temperature
        temperature_max_c = $counter.TemperatureMax
        wear_percent = $counter.Wear
        power_on_hours = $counter.PowerOnHours
        read_errors_total = $counter.ReadErrorsTotal
        write_errors_total = $counter.WriteErrorsTotal
        read_errors_uncorrected = $counter.ReadErrorsUncorrected
        write_errors_uncorrected = $counter.WriteErrorsUncorrected
    }
})
ConvertTo-Json -InputObject $rows -Depth 4 -Compress
'''

_NUMERIC = ('size_bytes', 'temperature_c', 'temperature_max_c', 'wear_percent',
            'power_on_hours', 'read_errors_total', 'write_errors_total',
            'read_errors_uncorrected', 'write_errors_uncorrected')
_TEXT = ('device_id', 'model', 'media_type', 'bus_type', 'health_status',
         'operational_status', 'reliability_status')


def _normalize(row):
    result = {key: str(row[key]) if row.get(key) not in (None, '') else None
              for key in _TEXT}
    for key in _NUMERIC:
        value = row.get(key)
        result[key] = value if type(value) is int and value >= 0 else None
    if result['temperature_max_c'] == 0:
        result['temperature_max_c'] = None
    if result['wear_percent'] is not None and result['wear_percent'] > 100:
        result['wear_percent'] = None
    return result


def disk_health_snapshot():
    """Return status and disks; missing counters remain None, not zero."""
    if sys.platform != 'win32':
        return {'status': 'unsupported_platform', 'disks': []}
    try:
        process = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', _SCRIPT],
            capture_output=True, encoding='utf-8', errors='replace', timeout=30,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=True)
        rows = json.loads(process.stdout.lstrip('\ufeff'))
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            return {'status': 'invalid_response', 'disks': []}
        return {'status': 'ok', 'disks': [_normalize(row) for row in rows]}
    except subprocess.TimeoutExpired:
        return {'status': 'timeout', 'disks': []}
    except (OSError, subprocess.CalledProcessError):
        return {'status': 'unavailable', 'disks': []}
    except ValueError:
        return {'status': 'invalid_response', 'disks': []}
