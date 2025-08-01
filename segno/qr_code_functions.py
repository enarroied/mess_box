from pathlib import Path

import segno
from PIL import Image


def create_qr_code(
    data,
    output_path="qr_code.png",
    center_image_path=None,
    dark_color="black",
    light_color="white",
    transparent_background=False,
    scale=8,
    border=4,
):
    """
    Create a QR code with optional center image and custom styling.

    Args:
        data (str): The text/data to encode in the QR code
        output_path (str): Path where the QR code image will be saved
        center_image_path (str, optional): Path to image to place in center of QR code
        dark_color (str): Color for dark areas (default: "black")
        light_color (str): Color for light areas (default: "white")
        transparent_background (bool): If True, background will be transparent (default: False)
        scale (int): Scale factor for QR code size (default: 8)
        border (int): Border size around QR code (default: 4)

    Returns:
        str: Path to the generated QR code image
    """
    qr = _create_base_qr(data)

    # If no center image, save directly
    if not center_image_path or not Path(center_image_path).exists():
        _save_qr_direct(
            qr,
            output_path,
            scale,
            border,
            dark_color,
            transparent_background,
            light_color,
        )
        return output_path

    # if Needs center image
    temp_path = Path("temp_qr.png")
    try:
        # Save QR to temp file
        _save_qr_to_temp(
            qr,
            temp_path,
            scale,
            border,
            dark_color,
            transparent_background,
            light_color,
        )

        qr_img = Image.open(temp_path)
        center_img = _prepare_center_image(
            center_image_path, qr_img.size, transparent_background
        )

        final_img = _add_center_image(qr_img, center_img)
        final_img.save(output_path)

    finally:
        _cleanup_temp_file(temp_path)

    return output_path


def _create_base_qr(data):
    """Create base QR code with high error correction."""
    return segno.make(data, error="H")


def _save_qr_direct(
    qr, output_path, scale, border, dark_color, transparent_background, light_color
):
    """Save QR code directly without temp file."""
    background = None if transparent_background else light_color
    qr.save(output_path, scale=scale, border=border, dark=dark_color, light=background)


def _save_qr_to_temp(
    qr, temp_path, scale, border, dark_color, transparent_background, light_color
):
    """Save QR code to temporary file."""
    background = None if transparent_background else light_color
    qr.save(temp_path, scale=scale, border=border, dark=dark_color, light=background)


def _prepare_center_image(center_image_path, qr_size, transparent_background):
    """Prepare center image with proper sizing and background."""
    center_img = Image.open(center_image_path)

    # Calculate and apply size
    qr_width, qr_height = qr_size
    center_size = min(qr_width, qr_height) // 5
    center_img.thumbnail((center_size, center_size), Image.Resampling.LANCZOS)

    # Add white background if transparent QR
    if transparent_background:
        center_img = _add_white_background(center_img)

    return center_img


def _add_white_background(center_img):
    """Add white background to center image."""
    bg_size = max(center_img.size) + 20
    bg = Image.new("RGBA", (bg_size, bg_size), (255, 255, 255, 255))

    bg_pos = ((bg_size - center_img.size[0]) // 2, (bg_size - center_img.size[1]) // 2)
    bg.paste(center_img, bg_pos)
    return bg


def _add_center_image(qr_img, center_img):
    """Add center image to QR code."""
    final_img = qr_img.copy()
    center_pos = _calculate_center_position(qr_img.size, center_img.size)

    if center_img.mode == "RGBA":
        final_img.paste(center_img, center_pos, center_img)
    else:
        final_img.paste(center_img, center_pos)

    return final_img


def _calculate_center_position(qr_size, center_size):
    """Calculate position to center the image."""
    qr_width, qr_height = qr_size
    center_width, center_height = center_size

    center_x = (qr_width - center_width) // 2
    center_y = (qr_height - center_height) // 2

    return (center_x, center_y)


def _cleanup_temp_file(temp_path):
    """Clean up temporary file using pathlib."""
    if temp_path.exists():
        temp_path.unlink()
