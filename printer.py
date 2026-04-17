import asyncio
from bleak import BleakClient, BleakScanner

# Phomemo D30 BLE UUIDs (FF service, reverse-engineered from official app)
SERVICE_UUID  = "0000ff00-0000-1000-8000-00805f9b34fb"
WRITE_UUID    = "0000ff02-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID   = "0000ff03-0000-1000-8000-00805f9b34fb"

PRINTER_NAMES = ["D30", "PHOMEMO", "Phomemo"]
CHUNK_SIZE = 128  # bytes per BLE write


def _build_header(width_bytes: int = 12, height: int = 320) -> bytes:
    """Phomemo init + ESC @ + GS v 0 0 raster header."""
    return bytes.fromhex("1f1124001b40") + bytes([
        0x1d, 0x76, 0x30, 0x00,
        width_bytes & 0xFF, (width_bytes >> 8) & 0xFF,
        height & 0xFF, (height >> 8) & 0xFF,
    ])


_FOOTER = bytes([0x1b, 0x64, 0x00])  # ESC d NUL — end print session


async def find_printer(timeout: float = 10.0, retries: int = 3):
    """Scan for a D30 and return the BleakDevice, or None."""
    for attempt in range(retries):
        devices = await BleakScanner.discover(timeout=timeout)
        for d in devices:
            if d.name and any(n.upper() in d.name.upper() for n in PRINTER_NAMES):
                return d
        if attempt < retries - 1:
            await asyncio.sleep(2)
    return None


async def list_printers(timeout: float = 10.0) -> list[tuple[str, str]]:
    devices = await BleakScanner.discover(timeout=timeout)
    return [
        (d.name, d.address)
        for d in devices
        if d.name and any(n.upper() in d.name.upper() for n in PRINTER_NAMES)
    ]


async def scan_printer_services(timeout: float = 5.0) -> str:
    """Return a human-readable dump of BLE services on the discovered printer."""
    device = await find_printer(timeout)
    if not device:
        return "No Phomemo printer found."

    lines = [f"Printer: {device.name}  ({device.address})", ""]
    async with BleakClient(device) as client:
        for service in client.services:
            lines.append(f"Service: {service.uuid}")
            for char in service.characteristics:
                lines.append(f"  Char:  {char.uuid}  [{', '.join(char.properties)}]")
    return "\n".join(lines)


async def print_data(image_bytes: bytes, width_bytes: int = 12, height: int = 320) -> str:
    """Locate the printer, send the raster image, return the printer name."""
    device = await find_printer()
    if not device:
        raise RuntimeError("Phomemo D30 not found. Make sure it's turned on and in range.")

    payload = _build_header(width_bytes, height) + image_bytes + _FOOTER

    async with BleakClient(device) as client:
        for i in range(0, len(payload), CHUNK_SIZE):
            await client.write_gatt_char(WRITE_UUID, payload[i:i + CHUNK_SIZE], response=True)
            await asyncio.sleep(0.01)

    return device.name
