"""Windows Package Manager (winget) update discovery and installation."""
import shutil
import re
import subprocess


def _run_winget(arguments, on_line):
    """Stream command output and return exit code; never invoke a shell."""
    executable = shutil.which('winget')
    if not executable:
        raise FileNotFoundError('winget was not found. Install or repair App Installer from Microsoft.')
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    with subprocess.Popen(
        [executable, *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1,
        creationflags=flags,
    ) as process:
        for line in process.stdout:
            if line.strip():
                on_line(line.rstrip())
        return process.wait()


def check_updates(on_line):
    """List upgrades without installing them."""
    return _run_winget(['upgrade', '--disable-interactivity'], on_line)


def upgrade_all(on_line):
    """Install available upgrades, allowing installer prompts where required."""
    return _run_winget(['upgrade', '--all'], on_line)


def upgrade_package(package_id, on_line):
    """Upgrade exactly one winget package by ID, without invoking a shell."""
    if not isinstance(package_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*', package_id):
        raise ValueError('Invalid winget package ID')
    return _run_winget(['upgrade', '--id', package_id, '--exact'], on_line)


def parse_upgrade_table(lines):
    """Parse English winget's fixed-width upgrade table.

    Winget pads columns according to terminal width. Adjacent values may have
    only one space (or none) when a name or ID fills its allotted width.
    Return None when the expected English header is not present.
    """
    clean = [re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', line).rstrip('\r\n')
             for line in lines]
    header_re = re.compile(r'^\s*Name\s+Id\s+Version\s+Available(?:\s+Source)?\s*$')
    for i, header in enumerate(clean):
        if not header_re.match(header):
            continue
        positions = []
        for label in ('Name', 'Id', 'Version', 'Available', 'Source'):
            match = re.search(r'(?<!\S)' + label + r'(?!\S)', header)
            if match:
                positions.append(match.start())
        if len(positions) < 4:
            return None
        rows = []
        for raw in clean[i + 1:]:
            stripped = raw.strip()
            if not stripped or re.fullmatch(r'[-\s]+', raw):
                continue
            if re.match(r'^\d+ upgrades? available\b', stripped, re.I):
                break
            if re.match(r'^\d+ packages? have version numbers', stripped, re.I):
                break
            # Use header column boundaries, not whitespace splitting. Winget
            # sometimes prints adjoining cells without two separating spaces.
            boundaries = positions + [len(raw)]
            cells = [raw[boundaries[j]:boundaries[j + 1]].strip()
                     for j in range(4)]
            name, package_id, installed, available = cells
            available = available.split()[0] if available else available
            if not all((name, package_id, installed, available)):
                continue
            if installed == available:
                continue
            # Reject footer messages accidentally aligned into table columns.
            if not re.search(r'\d', installed) or not re.search(r'\d', available):
                continue
            rows.append((name, package_id, installed, available))
        return rows
    return None
