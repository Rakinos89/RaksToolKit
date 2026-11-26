"""Read-only Windows network overview for RaksToolKit."""
import json
import subprocess

import psutil


POWERSHELL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$config = Get-NetIPConfiguration | Where-Object {
    $_.IPv4Address -and $_.NetAdapter.Status -eq 'Up' -and
    $_.IPv4Address.IPAddress -notlike '169.254.*'
} | Sort-Object @{Expression={if ($_.IPv4DefaultGateway) {0} else {1}}} | Select-Object -First 1
if ($null -eq $config) { '{}' ; exit 0 }
[pscustomobject]@{
  adapter = $config.InterfaceAlias
  ipv4 = @($config.IPv4Address | Select-Object -ExpandProperty IPAddress)[0]
  gateway = @($config.IPv4DefaultGateway | Select-Object -ExpandProperty NextHop)[0]
  dns = @($config.DNSServer.ServerAddresses | Where-Object { $_ -match '^\d{1,3}(\.\d{1,3}){3}$' })
} | ConvertTo-Json -Compress -Depth 4
"""


def normalize_network_info(raw, stats=None, addresses=None):
    """Turn Windows adapter data into stable display fields."""
    stats = stats if stats is not None else psutil.net_if_stats()
    addresses = addresses if addresses is not None else psutil.net_if_addrs()
    adapter = str(raw.get('adapter') or '')
    info = stats.get(adapter)
    mac = 'Not available'
    for addr in addresses.get(adapter, []):
        if addr.family == psutil.AF_LINK and addr.address:
            mac = addr.address
            break
    dns = raw.get('dns') or []
    if isinstance(dns, str):
        dns = [dns]
    speed = f'{info.speed} Mbps' if info and info.speed and info.speed > 0 else 'Not available'
    connected = bool(adapter and info and info.isup)
    return {
        'status': 'Connected' if connected else 'Disconnected',
        'adapter': adapter or 'Not available',
        'ipv4': raw.get('ipv4') or 'Not available',
        'gateway': raw.get('gateway') or 'Not available',
        'dns': ', '.join(str(item) for item in dns) or 'Not available',
        'mac': mac,
        'speed': speed,
    }


def get_network_overview():
    """Collect active Windows adapter data without changing network settings."""
    completed = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', POWERSHELL_SCRIPT],
        capture_output=True, text=True, errors='replace', timeout=20,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip() or 'Network query failed')
    try:
        raw = json.loads(completed.stdout.strip() or '{}')
    except json.JSONDecodeError as exc:
        raise RuntimeError('Unable to parse Windows network information') from exc
    if not isinstance(raw, dict):
        raise RuntimeError('Unexpected Windows network information format')
    return normalize_network_info(raw)
