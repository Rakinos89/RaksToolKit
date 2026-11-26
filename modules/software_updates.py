"""Read-only software update discovery using Windows Package Manager."""
import os
import shutil
import subprocess


def check_updates(on_line):
    """Stream winget's upgrade listing; return its exit code.

    This command only lists upgrades and never installs packages.
    """
    executable = shutil.which('winget')
    if not executable:
        raise FileNotFoundError('winget was not found. Install or repair App Installer from Microsoft.')
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    env = os.environ.copy()
    with subprocess.Popen(
        [executable, 'upgrade', '--disable-interactivity'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1,
        creationflags=flags,
        env=env,
    ) as process:
        for line in process.stdout:
            if line.strip():
                on_line(line.rstrip())
        return process.wait()
