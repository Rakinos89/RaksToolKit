"""Windows Package Manager (winget) update discovery and installation."""
import shutil
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
