# RaksToolKit

**A Windows maintenance, system monitoring, and gaming utility built with Python.**

RaksToolKit is an open-source Windows desktop application that brings practical system tools into one graphical interface. It provides monitoring, maintenance, gaming utilities, and privacy-conscious display options. Download the portable Windows build to use it without installing Python.

## Download for Windows

**Latest stable release: v1.0.0**

**[Download RaksToolKit v1.0.0 for Windows x64](https://github.com/Rakinos89/RaksToolKit/releases/tag/v1.0.0)**

Under **Assets**, download `RaksToolKit-v1.0.0-Windows-x64.zip`, extract the entire archive, and run `RaksToolKit.exe` from the extracted `RaksToolKit` folder. Keep the `_internal` folder beside the executable. **No separate Python installation or IDE required.**

See [Download and Run](#download-and-run-windows) for installation and security notes.

## Features

### System Dashboard
- Live CPU, RAM, and C: drive usage monitoring
- CPU model and core counts, total memory, and Windows version
- Privacy-aware display of the computer name

### Windows Maintenance
- DISM RestoreHealth and System File Checker (SFC)
- DNS cache flushing
- Administrator privilege detection and elevation
- Background execution with task output and error handling

### Smart Cleanup
- Scan user and Windows temporary folders for files older than 24 hours
- Preview eligible files and estimated space using Scan or Dry Run
- Confirm before deletion; skip inaccessible files and symbolic links

### Gaming & Performance
- NVIDIA GPU monitoring via `nvidia-smi`, including utilization, temperature, VRAM, clocks, and power where available
- Automatic GPU updates every two seconds on the Gaming page
- Scrollable dashboard with GPU metric cards and usage bars
- Detection of selected running game processes
- Windows power plan management and TCP connection latency testing
- Modular monitoring code for future GPU vendor support; AMD monitoring is not yet verified

### Privacy Mode
- Settings toggle to mask supported computer name, username, and IPv4 text displayed in the app
- Preference persists between restarts
- Display masking is not complete anonymization; logs and external applications are not automatically redacted

### Activity Logging
- Persistent local maintenance activity history
- Task results and error reporting
- AppData storage under the RaksToolKit application name, with migration of supported older WinToolKit data

## Requirements
- Windows 10 or Windows 11 (64-bit)
- For source-code use only: Python 3.10 or newer and dependencies in `requirements.txt`
- NVIDIA GPU metrics require a compatible NVIDIA driver and `nvidia-smi`; other adapters may show unavailable metrics

Some maintenance operations require administrator privileges.

## Screenshots

These screenshots may show an earlier interface version; updated RaksToolKit screenshots can replace them later.

### Dashboard
![RaksToolKit Dashboard](assets/screenshots/rakstoolkit_dashboard.png)

### Maintenance
![RaksToolKit Maintenance](assets/screenshots/rakstoolkit_maintenance.png)

### Gaming
![RaksToolKit Gaming](assets/screenshots/rakstoolkit_gaming.png)

### Activity History
![RaksToolKit Activity History](assets/screenshots/rakstoolkit_activity.png)

## Download and Run (Windows)

1. Open the [v1.0.0 GitHub release](https://github.com/Rakinos89/RaksToolKit/releases/tag/v1.0.0).
2. Download `RaksToolKit-v1.0.0-Windows-x64.zip` from **Assets**, not the automatically generated source-code archive.
3. Extract the entire ZIP to a folder of your choice.
4. Open the extracted `RaksToolKit` folder and double-click `RaksToolKit.exe`. Keep the `_internal` folder alongside the executable.

The portable build does not require a separate Python installation. Some maintenance features request administrator privileges. Download only from the official repository; Windows may show a security warning for an unsigned executable.

## Installation from Source (Developers)

Clone the repository:

```powershell
git clone https://github.com/Rakinos89/RaksToolKit.git
cd RaksToolKit
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
| v0.9 | Portable Windows executable, application icon, distribution ZIP, refresh feedback | Complete |
| Pre-v1.0 | Documentation, license, automated testing, reliability and UI improvements | Complete |
| v1.0.0 | Stable release, RaksToolKit branding, and final packaging | Released |
| Future | AMD GPU monitoring and additional hardware support | Planned |

## Building a Windows Release

From the repository root, on Windows with a configured `.venv` and PyInstaller installed:

```powershell
.\build.ps1
```

The script uses PyInstaller from the virtual environment, bundles the application icon, builds the executable, and writes the portable ZIP and a SHA-256 checksum into `dist`. It does not upload or publish a GitHub release. The icon must exist at `assets/icons/rakstoolkit.ico`.

## Technology Stack
- **Python:** Application logic
- **CustomTkinter:** Desktop interface
- **psutil:** System and process monitoring
- **Windows utilities:** Diagnostics and maintenance
- **PyInstaller:** Windows portable build
- **Git & GitHub:** Version control and releases

## Project Status

**Current stable version: v1.0.0**

RaksToolKit is under active development. GPU monitoring availability varies by hardware and driver. Future releases will expand hardware support and functionality.

## Disclaimer

RaksToolKit is an independent development project. System maintenance and cleanup operations can modify or delete files. Review actions carefully and use the application at your own risk.

## License

Licensed under the **MIT License**. See [LICENSE](LICENSE) for the full terms and copyright notice.
