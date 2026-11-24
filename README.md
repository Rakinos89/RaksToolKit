# WinToolKit

**A Windows maintenance, system monitoring, and gaming utility built with Python.**

WinToolKit is an open-source desktop application that brings practical Windows tools into one graphical interface. Development is incremental, with features tested before each release.

## Features

### System Dashboard
- Live CPU, RAM, and C: drive usage monitoring
- CPU model and core counts, total memory, and Windows version
- Privacy-aware display of the computer name

### Windows Maintenance
- DISM RestoreHealth and System File Checker (SFC)
- DNS cache flushing
- Administrator privilege detection and elevation
- Background execution with task output

### Smart Cleanup
- Scan user and Windows temporary folders for files older than 24 hours
- Preview eligible files and space using Scan or Dry Run
- Confirm before deletion; skip inaccessible files and symbolic links

### Gaming & Performance
- NVIDIA GPU monitoring via `nvidia-smi`, including utilization, temperature, VRAM, clocks, and power where available
- Automatic GPU updates every two seconds on the Gaming page
- Scrollable dashboard with GPU metric cards and usage bars
- Detection of selected running game processes
- Windows power plan management and TCP connection latency testing
- Modular monitoring code designed for future GPU vendor support; AMD monitoring is not yet verified

### Privacy Mode
- Settings toggle to mask supported computer name, username, and IPv4 text displayed in the app
- Preference persists between restarts
- Display masking is not complete anonymization; logs and external applications are not automatically redacted

### Activity Logging
- Persistent local maintenance activity history
- Task results and error reporting

## Requirements
- Windows 10 or Windows 11
- Python 3.10 or newer
- Dependencies listed in `requirements.txt`
- NVIDIA GPU metrics require a compatible NVIDIA driver and `nvidia-smi`; other adapters may show unavailable metrics

Some maintenance operations require administrator privileges.

## Screenshots

*Screenshots below were captured during earlier development and may not reflect the latest v0.8 interface.*

### Dashboard
![WinToolKit Dashboard](assets/screenshots/wintoolkit_dashboard.png)

### Maintenance
![WinToolKit Maintenance](assets/screenshots/wintoolkit_maintenance.png)

### Gaming
![WinToolKit Gaming](assets/screenshots/wintoolkit_gaming.png)

## Installation

Clone the repository:

```powershell
git clone https://github.com/Rakinos89/WinToolKit.git
cd WinToolKit
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Install dependencies without requiring PowerShell script activation:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Launch:

```powershell
.\.venv\Scripts\python.exe main.py
```

## Development Roadmap

| Version | Milestone | Status |
|---|---|---|
| v0.1–v0.3 | Dashboard and navigation | Complete |
| v0.4 | Windows repair tools | Complete |
| v0.5 | Smart Cleanup | Complete |
| v0.6 | Improved UI and activity logging | Complete |
| v0.7 | Gaming and performance tools | Complete |
| v0.8 | Extended NVIDIA monitoring, live Gaming dashboard, Privacy Mode, CPU identification | Complete |
| Future | AMD GPU monitoring and additional hardware support | Planned |

## Technology Stack
- **Python:** Application logic
- **CustomTkinter:** Desktop interface
- **psutil:** System and process monitoring
- **Windows utilities:** Diagnostics and maintenance
- **Git & GitHub:** Version control

## Project Status

**Current version: v0.8.0**

WinToolKit is actively developed and tested incrementally. GPU monitoring availability varies by hardware and driver.

## Disclaimer

WinToolKit is an independent development project. System maintenance and cleanup operations can modify or delete files. Review actions carefully and use the application at your own risk.

## License

No license has been selected yet.
