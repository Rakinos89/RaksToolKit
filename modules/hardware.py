"""Windows hardware identification with safe fallbacks."""
import platform
import re


def cpu_name():
    """Read the processor's marketing name from the Windows registry."""
    try:
        import winreg
        path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        name = re.sub(r"\s+", " ", str(name)).strip()
        if name:
            return name
    except (ImportError, OSError, ValueError, TypeError):
        pass
    return platform.processor() or "Unknown"


def windows_name():
    """Use Windows 11 branding where build numbers distinguish it from 10."""
    if platform.system() == "Windows":
        try:
            build = int(platform.version().split(".")[-1])
            if build >= 22000:
                return "Windows 11"
            if build >= 10240:
                return "Windows 10"
        except (ValueError, IndexError):
            pass
    return f"{platform.system()} {platform.release()}"
