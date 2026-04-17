#!/usr/bin/env python3
import asyncio
import sys
import click
from image import create_label_image, image_to_bytes
from printer import print_data, list_printers, scan_printer_services


@click.group()
def cli():
    """Phomemo D30 label printer CLI."""


@cli.command()
@click.argument("text")
@click.option("--font", "font_path", help="Path to a .ttf font file.")
@click.option("--size", "font_size", type=int, help="Font size in pixels (auto-fits if omitted).")
@click.option("--preview", "preview_path", metavar="FILE", help="Save a preview PNG instead of printing.")
def print(text, font_path, font_size, preview_path):
    """Print TEXT on the D30 label maker."""
    img = create_label_image(text, font_path=font_path, font_size=font_size)

    if preview_path:
        # Save a readable preview (rotate back to landscape)
        preview = img.rotate(-90, expand=True)
        preview.save(preview_path)
        click.echo(f"Preview saved to {preview_path}")
        return

    data = image_to_bytes(img)
    try:
        name = asyncio.run(print_data(data))
        click.echo(f"Printed on {name}")
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command(name="list")
@click.option("--timeout", default=5.0, show_default=True, help="BLE scan timeout in seconds.")
def list_cmd(timeout):
    """Scan for nearby Phomemo printers."""
    click.echo(f"Scanning for {timeout}s…")
    devices = asyncio.run(list_printers(timeout=timeout))
    if not devices:
        click.echo("No Phomemo printers found.")
    else:
        for name, addr in devices:
            click.echo(f"  {name}  —  {addr}")


@cli.command()
@click.option("--timeout", default=5.0, show_default=True, help="BLE scan timeout in seconds.")
def scan(timeout):
    """Show BLE services and characteristics of the D30 (useful for debugging)."""
    click.echo(f"Scanning for {timeout}s…")
    result = asyncio.run(scan_printer_services(timeout=timeout))
    click.echo(result)


if __name__ == "__main__":
    cli()
