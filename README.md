# MaterialSnap — Modern Material You Screenshot Utility

A lightweight, responsive screenshot tool for Windows 10/11 designed with **Google Material You** aesthetics, dynamic rounded pills, gradient accents, zero idle CPU overhead, and native multi-monitor HiDPI capture.

---

## ✨ Features

- **Google Material You Aesthetic**: Deep dark matte background (`#1E1F22`), dynamic gradient borders (`#8AB4F8`, `#C58AF9`, `#81C995`), smooth rounded pills, and Google Sans typography.
- **Freeze Screen Overlay**: Instant multi-screen freeze with dark translucent scrim and crisp cutout selection.
- **Google Search Pill Action Bar**: Floating pill toolbar beside your selection with 1-click **Copy**, **Save to Disk**, **Full Screen Snip**, and **Cancel**.
- **Precision Loupe Magnifier**: Real-time 8x zoom magnifier with pixel grid and RGB hex color code readout.
- **Silent Background System Tray**: Runs silently in the system tray (<40MB RAM, 0% idle CPU).
- **Global Hotkeys**: Default `Ctrl + Shift + S` and `PrintScreen` (customizable via Settings).
- **Windows Autostart**: One-click enable/disable launch on Windows boot via Registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).
- **Smooth Toast Notifications**: Non-intrusive floating toasts with "Open Folder" quick action.

---

## 🚀 Quick Start

### 1. Requirements
- Windows 10 / Windows 11
- Python 3.10+

### 2. Install Dependencies & Run
Simply double-click `run.bat` or run:

```bash
pip install -r requirements.txt
python main.py
```

---

## ⌨️ Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl + Shift + S` or `PrintScreen` | Trigger Screenshot Overlay |
| `Left Mouse Drag` | Select capture region |
| `Enter` or `Ctrl + C` | Copy selection to clipboard |
| `Ctrl + S` | Save screenshot to default directory |
| `Shift + Click Save` | Choose folder and filename to save |
| `F` | Select entire screen |
| `Esc` or `Right Click` | Cancel / Close overlay |
