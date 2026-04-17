# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python CLI to print labels on a **Phomemo D30** Bluetooth thermal label printer. Target platform: macOS (BLE via CoreBluetooth through `bleak`). Mobile support (Flutter) is planned for later.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

macOS will prompt for Bluetooth permission on first run — approve it in System Settings → Privacy & Security → Bluetooth.

## Commands

```bash
# Print a label
python label.py print "Hello World"

# Multi-line label
python label.py print $'Line 1\nLine 2'

# Custom font / fixed size
python label.py print "Hello" --font /path/to/font.ttf --size 48

# Save a preview image instead of printing
python label.py print "Hello" --preview preview.png

# Discover nearby printers
python label.py list

# Dump BLE services (debug UUIDs if printing fails)
python label.py scan
```

## Architecture

| File | Role |
|------|------|
| `label.py` | Click CLI — three commands: `print`, `list`, `scan` |
| `image.py` | Text → 96×320 px raster image; packs to printer bytes |
| `printer.py` | BLE discovery, connection, and data transfer |

### Protocol (reverse-engineered from official Android app)

- **BLE service UUID**: `0000ff00-0000-1000-8000-00805f9b34fb`
- **Write characteristic**: `0000ff02-0000-1000-8000-00805f9b34fb`
- **Notify characteristic**: `0000ff03-0000-1000-8000-00805f9b34fb`
- **Packet structure**: 14-byte header (`1f1124001b40` + GS v 0 0 raster command) + 3840 bytes image + `1b6400` footer
- **Chunk size**: 128 bytes per BLE write with response

### Image pipeline

1. Create landscape canvas (320 × 96 px, white)
2. Draw centered text — auto-sizes font to fit, supports multi-line
3. Rotate 90° CCW → portrait (96 × 320 px) — this is what the printer expects
4. Pack to bytes: 12 bytes per row (1 bit per pixel, MSB-first, 1=black), 320 rows = 3840 bytes total

### Label dimensions

- Tape: 12mm wide = 96 px at 203 DPI
- Default label length: ~40mm = 320 px
- Width is fixed; length could be made configurable by adjusting the raster header height bytes and canvas size
