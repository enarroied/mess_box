import io
import sys

import requests
from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich_pixels import Pixels

console = Console()


def download_image(url: str) -> Image.Image:
    response = requests.get(url, timeout=20)
    response.raise_for_status()

    return Image.open(io.BytesIO(response.content))


def main():
    if len(sys.argv) < 2:
        console.print(
            Panel.fit(
                "Usage:\n\npython viewer.py <image_url>",
                title="Rich Image Viewer",
            )
        )
        raise SystemExit(1)

    url = sys.argv[1]

    console.print(f"[bold cyan]Downloading:[/] {url}\n")

    try:
        image = download_image(url)

        # Resize for terminal friendliness
        image.thumbnail((120, 60))

        pixels = Pixels.from_image(image)

        console.print(pixels)

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
