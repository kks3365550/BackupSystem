# BackupSystem: Enterprise Zero-Cloud Hybrid Backup & 3-Tier Disaster Recovery Engine

[![Version](https://img.shields.io/badge/version-v2.10.6-blue.svg?style=flat-square)](https://github.com/kks3365550/BackupSystem/releases)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011%20%7C%20Server-0078D6.svg?style=flat-square&logo=windows)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg?style=flat-square&logo=python)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/architecture-x86__64-informational.svg?style=flat-square)](#architecture-overview)
[![License](https://img.shields.io/badge/license-Enterprise%20Proprietary-red.svg?style=flat-square)](#license)
[![Zero Cloud Dependency](https://img.shields.io/badge/dependency-Zero--Cloud%20Air--Gapped-success.svg?style=flat-square)](#deterministic-content-addressed-storage-cas)

An enterprise-grade, deterministic Windows backup orchestration and disaster recovery system designed for air-gapped, zero-cloud, and compliance-sensitive environments. **BackupSystem** combines immutable Content-Addressed Storage (CAS), non-intrusive Volume Shadow Copy Service (VSS) live captures, Windows Bare-Metal Recovery (BMR), and cryptographically verified self-updating pipelines.

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Architecture Overview](#architecture-overview)
- [Core Architectural Pillars](#core-architectural-pillars)
  - [1. Deterministic Content-Addressed Storage (CAS)](#1-deterministic-content-addressed-storage-cas)
  - [2. Zero-Lock Live Backups via Volume Shadow Copy (VSS)](#2-zero-lock-live-backups-via-volume-shadow-copy-vss)
  - [3. 3-Tier Disaster Recovery Architecture](#3-3-tier-disaster-recovery-architecture)
  - [4. Non-Elevated Least-Privilege Runtime & Hardened ACL](#4-non-elevated-least-privilege-runtime--hardened-acl)
  - [5. Sub-15ms Invalidation-Driven Metadata Caching](#5-sub-15ms-invalidation-driven-metadata-caching)
  - [6. Ghost/Silent Background Automation (Zero Window Flickering)](#6-ghostsilent-background-automation-zero-window-flickering)
  - [7. Cryptographically Verified Over-the-Air (OTA) Updates](#7-cryptographically-verified-over-the-air-ota-updates)
  - [8. Lifecycle-Aware Inno Setup 6+ Installer Engine](#8-lifecycle-aware-inno-setup-6-installer-engine)
- [Directory Structure](#directory-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Enterprise Installer Deployment](#enterprise-installer-deployment)
  - [Developer / Portable CLI Execution](#developer--portable-cli-execution)
- [Web Management Dashboard](#web-management-dashboard)
- [Configuration Specification (`profiles.json`)](#configuration-specification-profilesjson)
- [Disaster Recovery Runbooks](#disaster-recovery-runbooks)
- [Release Verification & Integrity](#release-verification--integrity)
- [License & Support](#license--support)

---

## Executive Summary

Standard enterprise backup tools often introduce external cloud dependencies, complex license servers, or severe performance overhead during file enumeration. **BackupSystem** was engineered to solve these challenges in mission-critical industrial and enterprise environments:

- **100% On-Premises & Air-Gapped**: Zero telemetry or cloud dependencies; all snapshots reside on local repositories or private network-attached storage.
- **Enterprise Windows Compliance**: Full native integration with Windows VSS (`vssadmin`), Bare-Metal Recovery (`wbadmin`), Task Scheduler (`Register-ScheduledTask`), and Windows Credential/UAC isolation.
- **Microsecond Precision & Storage Efficiency**: Block-level chunking and SHA-256 deduplication reduce repository footprint by 60–85% across daily incremental snapshots.

---

## Architecture Overview

```
                               ┌──────────────────────────────────────────────┐
                               │             Operator Interfaces              │
                               │  ┌──────────────────────┐  ┌──────────────┐  │
                               │  │ Modern HTML5 Web UI  │  │ Windows Tray │  │
                               │  │   (Port 8765, SSE)   │  │ (pystray)    │  │
                               │  └──────────┬───────────┘  └──────┬───────┘  │
                               └─────────────┼─────────────────────┼──────────┘
                                             │ HTTP REST / SSE     │ Native RPC
                                             ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BackupSystem Host Runtime (Non-Elevated)                 │
│                                                                             │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────┐  │
│  │ SnapshotMetadataCache │  │  Profile & Auth Guard │  │  OTA Engine     │  │
│  │ (~11ms on 220k files) │  │  (HMAC SHA-256, RBAC) │  │  (GitHub API)   │  │
│  └──────────┬────────────┘  └──────────┬────────────┘  └────────┬────────┘  │
│             │                          │                        │           │
│             ▼                          ▼                        ▼           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     Core Backup & Snapshot Engine                     │  │
│  │   - Worker Pool (Multi-threaded SHA-256 Hashing & Chunk Deduplication)│  │
│  │   - Exclusion Evaluator (Regex, Glob, System Directory Blacklist)     │  │
│  └──────────────────────────────────┬────────────────────────────────────┘  │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
┌───────────────────────────┐                   ┌───────────────────────────┐
│ Windows VSS Bridge (UAC)  │                   │ Immutable Repository      │
│ - Live open-file locks    │                   │ - Content-Addressed Blobs │
│ - Volume snapshot shadow  │                   │ - Metadata Manifests JSON │
│ - Windows wbadmin (BMR)   │                   │ - Zstandard Compression   │
└───────────────────────────┘                   └───────────────────────────┘
```

---

## Core Architectural Pillars

### 1. Deterministic Content-Addressed Storage (CAS)
Every ingested file is processed through a deterministic streaming hash pipeline (SHA-256). Files sharing identical bitstreams are stored as a single immutable compressed blob (`.blob`), drastically minimizing storage requirements across overlapping snapshot trees.
- **Immutable Storage**: Snapshots are metadata manifests referencing immutable content hashes.
- **Atomic Commits**: Snapshot entries are staged in temporary transaction buffers before being committed to the manifest database, preventing corrupt index states upon power failure or process termination.

### 2. Zero-Lock Live Backups via Volume Shadow Copy (VSS)
Enterprise workloads inevitably maintain exclusive write locks on production databases, PST files, and active system logs.
- BackupSystem delegates live snapshot requests to the Windows Volume Shadow Copy Service subsystem.
- Captures point-in-time volume snapshots (`\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy*`), allowing 100% read consistency without interrupting running host services or database engines.

### 3. 3-Tier Disaster Recovery Architecture
Disasters vary from accidental file deletion to total hardware incineration. BackupSystem enforces a tiered recovery matrix:

| Recovery Tier | Scenario | Recovery Mechanism | Typical RTO |
| :--- | :--- | :--- | :--- |
| **Tier 1: Point-in-Time CAS Rollback** | Accidental deletion, file corruption, or ransomware | Web Dashboard / CLI file-tree rollback directly from CAS manifests | **< 3 Minutes** |
| **Tier 2: Bare-Metal Recovery (BMR)** | Windows OS corruption, registry failure, unbootable disk | Integration with Windows Native `wbadmin` system state images via Windows Recovery Environment (WinRE) | **15–30 Minutes** |
| **Tier 3: Standalone Emergency DR** | Total application corruption or environment isolation | Self-contained zero-dependency Python script (`tools/disaster_recovery.py`) capable of parsing raw blobs without the server running | **Immediate** |

### 4. Non-Elevated Least-Privilege Runtime & Hardened ACL
Prior to version `v2.10.4`, running background services in `C:\Program Files` frequently encountered `WinError 5 (Access is Denied)` unless granted full administrative privileges. BackupSystem resolves this through precise Windows Discretionary Access Control Lists (DACL):
- **Binaries & Core (`C:\Program Files\백업시스템`)**: Read-and-Execute only for standard `Users`; modifications restricted strictly to `Administrators` and `SYSTEM`.
- **Mutable State (`{app}\data` & `{app}\logs`)**: Explicit `Users: Modify` inheritance configured directly at the Inno Setup filesystem layer:
  ```iss
  [Dirs]
  Name: "{app}\data"; Permissions: users-modify
  Name: "{app}\logs"; Permissions: users-modify
  ```
- Protects binary integrity against tampering while enabling normal non-elevated user execution for daily scheduled backups and system tray operation.

### 5. Sub-15ms Invalidation-Driven Metadata Caching
In repositories containing over 220,000 files and deep directory hierarchies, naive recursive scanning causes severe disk I/O bottlenecks and high UI latency.
- BackupSystem features an in-memory `SnapshotMetadataCache` with timestamp- and size-driven invalidation.
- Warm-cache manifest resolution benchmarks at **~11ms** across 220,000+ indexed files, delivering instant response times across the Web Dashboard.

### 6. Ghost/Silent Background Automation (Zero Window Flickering)
Windows batch scripts (`.bat`) invoked by the Windows Task Scheduler (`schtasks`) frequently produce brief black console popups that interrupt active users.
- **Ghost Invocation Protocol**: All scheduled background tasks are executed through custom VBScript wrappers (`wscript.exe`) utilizing `SW_HIDE (Window Style 0)`:
  ```vbs
  Set WshShell = CreateObject("WScript.Shell")
  WshShell.Run "pythonw.exe run.py --backup-profile default", 0, False
  ```
- External subprocess invocations within Python strictly enforce `creationflags=subprocess.CREATE_NO_WINDOW`, eliminating desktop interruptions.

### 7. Cryptographically Verified Over-the-Air (OTA) Updates
The auto-update engine communicates securely with the official GitHub Releases API without depending on peer-to-peer relay nodes:
1. **Manifest Validation**: Release manifests are checked for semantic version progression (`semver`).
2. **Cryptographic Checksumming**: SHA-256 hashes of incoming installer payloads (`Setup.exe`) are validated before staging.
3. **UAC Boundary Isolation**: Update payload execution explicitly triggers Windows UAC elevation, preserving strict separation between runtime operation and binary replacement.

### 8. Lifecycle-Aware Inno Setup 6+ Installer Engine
Version `v2.10.6` implements advanced installer lifecycle hooks to eliminate Windows "File in Use" locks during upgrades and uninstalls:
- **`InitializeSetup` Win32 Detection**: Custom Pascal scripting scans for listening ports (8765) and processes before initiating file copies.
- **Targeted Process Termination**: Gracefully signals system tray and web worker processes, terminating only processes matching the application's unique executable path.
- **Directive Enforcement**: Configured with `CloseApplications=force` and `RestartApplications=no` for deterministic enterprise deployment.

---

## Directory Structure

```text
백업시스템/
├── core/                         # Core backup & snapshot engine
│   ├── backup.py                 # Core orchestration & worker dispatch
│   ├── cas.py                    # Content-Addressed Storage & blob indexing
│   ├── vss.py                    # Windows Volume Shadow Copy Service wrapper
│   ├── scheduler.py              # Windows Task Scheduler automation
│   ├── metadata_cache.py         # Sub-15ms in-memory manifest cache
│   └── crypto.py                 # Streaming SHA-256 & integrity checkers
├── web/                          # Web UI server & API backend
│   ├── app.py                    # FastAPI/Starlette dashboard server (Port 8765)
│   ├── sse.py                    # Real-time Server-Sent Events stream
│   ├── static/                   # CSS, Vanilla JS, and UI assets
│   └── templates/                # Responsive HTML5 dashboards
├── tray/                         # Windows system tray integration
│   ├── tray_app.py               # pystray integration & notification hooks
│   └── icon.ico                  # Application system tray asset
├── tools/                        # Operational tooling & release utilities
│   ├── disaster_recovery.py      # Tier 3 standalone recovery CLI
│   ├── release.py                # Zero-touch semantic release pipeline
│   ├── update_checker.py         # Direct GitHub Releases API client
│   └── verify_integrity.py       # Snapshot manifest verification suite
├── scripts/                      # Windows automation & launcher scripts
│   ├── start_silent.vbs          # Ghost background launcher (SW_HIDE)
│   ├── start_tray.vbs            # System tray launcher
│   └── stop_backup_system.bat    # Safe process-tree terminator
├── installer/                    # Inno Setup compilation sources
│   └── BackupSystem.iss          # Inno Setup 6+ manifest with DACL config
├── data/                         # Mutable user state (DACL: Users Modify)
│   ├── profiles.json             # Backup targets & exclusion rules
│   └── auth.json                 # Dashboard credentials & HMAC salts
├── logs/                         # Rolling execution logs (DACL: Users Modify)
│   └── backup_system.log
├── run.py                        # Unified CLI and application bootstrap
└── VERSION                       # Semantic version descriptor (v2.10.6)
```

---

## Getting Started

### Prerequisites
- **Operating System**: Windows 10 (1809+), Windows 11, or Windows Server 2016/2019/2022 (x86_64).
- **Runtimes**: Python 3.10+ (included in standard enterprise installer package).
- **Privileges**: Standard user permissions for daily operation; Administrator elevation required only during initial installer setup.

### Enterprise Installer Deployment
1. Download the latest `BackupSystem_Setup_vX.Y.Z.exe` from [GitHub Releases](https://github.com/kks3365550/BackupSystem/releases).
2. Execute the installer with standard administrator rights:
   ```cmd
   BackupSystem_Setup_v2.10.6.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
   ```
3. The installer automatically configures:
   - File permission inheritance (`Users: Modify` for `data/` and `logs/`).
   - Windows Startup registration (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).
   - Default backup schedule in Windows Task Scheduler.

### Developer / Portable CLI Execution
For portable environments or source installations:

```powershell
# 1. Clone repository
git clone https://github.com/kks3365550/BackupSystem.git
cd BackupSystem

# 2. Install production dependencies
pip install -r requirements.txt

# 3. Initialize default profiles and DACL permissions
python run.py --init

# 4. Execute an immediate backup using the default profile
python run.py --backup --profile default

# 5. Launch the Web Management Dashboard
python run.py --server --port 8765
```

---

## Web Management Dashboard

The integrated dashboard runs locally at `http://127.0.0.1:8765` and provides full administrative control without external internet dependencies:

- **Live Progress Tracking**: Server-Sent Events (SSE) broadcast real-time throughput (MB/s), file ingestion count, and deduplication efficiency.
- **Point-in-Time Explorer**: Browse previous snapshot generations, search by filename or pattern, and initiate single-file or recursive directory restorations.
- **Storage Metrics**: Visual breakdown of raw dataset size versus compressed, deduplicated CAS repository footprint.
- **Audit Logs**: Filterable execution traces, VSS allocation notices, and task scheduler completion statuses.

---

## Configuration Specification (`profiles.json`)

Backup targets and schedules are managed deterministically via `data/profiles.json`:

```json
{
  "profiles": {
    "default": {
      "name": "Production Data & Documents",
      "sources": [
        "C:\\Users\\Administrator\\Documents",
        "D:\\ProductionDB"
      ],
      "destination": "E:\\Backups\\Repository",
      "vss_enabled": true,
      "compression": "zstd",
      "compression_level": 3,
      "exclusions": {
        "patterns": ["*.tmp", "~$*", "*.cache"],
        "directories": ["node_modules", ".git", "AppData\\Local\\Temp"]
      },
      "retention": {
        "keep_daily": 7,
        "keep_weekly": 4,
        "keep_monthly": 12
      }
    }
  }
}
```

---

## Disaster Recovery Runbooks

### Runbook 1: Tier 1 Single File or Folder Rollback
1. Open the Web Dashboard (`http://127.0.0.1:8765`).
2. Navigate to **Snapshots** and select the desired point-in-time timestamp.
3. Locate the target file or directory in the manifest browser.
4. Click **Restore**, choose target path (in-place or alternate directory), and confirm.

### Runbook 2: Tier 3 Standalone CLI Emergency Restore
In the event of complete application or database corruption where the Web UI cannot be served:

```powershell
# Syntax: python tools/disaster_recovery.py --repo <REPO_DIR> --snapshot <SNAPSHOT_ID> --target <RESTORE_DIR>
python tools/disaster_recovery.py `
  --repo "E:\Backups\Repository" `
  --snapshot "latest" `
  --target "C:\RestoredData"
```
*The standalone recovery tool operates with standard Python library modules and has zero external dependencies.*

---

## Release Verification & Integrity

All official release binaries are compiled via clean-room GitHub Actions workflows and signed with cryptographic checksums.

To verify the integrity of your local deployment:

```powershell
# Compute SHA-256 hash of downloaded installer
Get-FileHash -Algorithm SHA256 .\BackupSystem_Setup_v2.10.6.exe

# Compare with published release manifest
python tools/verify_integrity.py --binary .\BackupSystem_Setup_v2.10.6.exe
```

---

## Windows Enterprise Compliance

- **Line Ending Integrity**: All scripts (`.bat`, `.cmd`, `.vbs`, `.py`, `.json`, `.iss`) strictly enforce Windows Standard CRLF (`\r\n`) line endings.
- **UAC Isolation**: Clear boundary separation between unprivileged runtime execution (`data/`, `logs/`) and administrative setup/update operations (`Program Files`).
- **Telemetry Free**: No data packets leave the host boundary; zero external API calls except when explicitly checking for updates via GitHub.

---

## License & Support

Distributed under an **Enterprise Proprietary License**. Unauthorized distribution, reverse engineering, or cloud hosting is prohibited.

For technical inquiries, bug reports, and deployment audits, please open an issue in the official [GitHub Issue Tracker](https://github.com/kks3365550/BackupSystem/issues).
