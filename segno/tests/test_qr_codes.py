import shutil
import sys
import tempfile
from pathlib import Path

import pytest
import segno
from PIL import Image

# Add parent directory to path to import from parent folder
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import your QR code functions from parent directory
# Change 'qr_code_functions' to whatever your actual filename is
from qr_code_functions import (
    _add_white_background,
    _calculate_center_position,
    _create_base_qr,
    _prepare_center_image,
    create_qr_code,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    test_dir = Path(tempfile.mkdtemp())
    yield test_dir
    shutil.rmtree(test_dir)


@pytest.fixture
def test_image(temp_dir):
    """Create a small test image for testing."""
    test_image_path = temp_dir / "test_logo.png"
    img = Image.new("RGB", (50, 50), color="red")
    img.save(test_image_path)
    return test_image_path


@pytest.fixture
def test_output(temp_dir):
    """Create test output path."""
    return temp_dir / "test_qr.png"


def test_create_base_qr():
    """Test that base QR code is created correctly."""
    qr = _create_base_qr("Hello World")

    assert isinstance(qr, segno.QRCode)
    assert qr.error == "H"  # High error correction (segno uses uppercase)


def test_calculate_center_position():
    """Test center position calculation."""
    qr_size = (200, 200)
    center_size = (50, 50)

    pos = _calculate_center_position(qr_size, center_size)

    assert pos == (75, 75)


@pytest.mark.parametrize(
    "qr_size,center_size,expected",
    [
        ((200, 200), (50, 50), (75, 75)),
        ((300, 200), (60, 40), (120, 80)),
        ((100, 100), (20, 20), (40, 40)),
    ],
)
def test_calculate_center_position_parametrized(qr_size, center_size, expected):
    """Test center position calculation with different sizes."""
    pos = _calculate_center_position(qr_size, center_size)
    assert pos == expected


def test_add_white_background():
    """Test adding white background to center image."""
    original_img = Image.new("RGBA", (30, 30), color="blue")

    result_img = _add_white_background(original_img)

    assert result_img.size[0] > original_img.size[0]
    assert result_img.size[1] > original_img.size[1]
    assert result_img.mode == "RGBA"


def test_create_basic_qr_code(test_output):
    """Test creating a basic QR code without center image."""
    result_path = create_qr_code("Test Data", str(test_output))

    assert Path(result_path).exists()

    img = Image.open(result_path)
    assert isinstance(img, Image.Image)
    assert img.size[0] > 0
    assert img.size[1] > 0


@pytest.mark.parametrize(
    "dark_color,light_color",
    [
        ("red", "blue"),
        ("green", "yellow"),
        ("black", "white"),
        ("#FF0000", "#00FF00"),
    ],
)
def test_create_qr_code_with_custom_colors(test_output, dark_color, light_color):
    """Test creating QR code with different color combinations."""
    result_path = create_qr_code(
        "Test Data", str(test_output), dark_color=dark_color, light_color=light_color
    )

    assert Path(result_path).exists()

    img = Image.open(result_path)
    assert isinstance(img, Image.Image)


def test_create_qr_code_with_transparent_background(test_output):
    """Test creating QR code with transparent background."""
    result_path = create_qr_code(
        "Test Data", str(test_output), transparent_background=True
    )

    assert Path(result_path).exists()

    img = Image.open(result_path)
    # PNG with transparency should be RGBA or P mode, not always RGBA/LA
    assert img.mode in ["RGBA", "LA", "P", "1"]


def test_create_qr_code_with_center_image(test_output, test_image):
    """Test creating QR code with center image."""
    result_path = create_qr_code(
        "Test Data", str(test_output), center_image_path=str(test_image)
    )

    assert Path(result_path).exists()

    img = Image.open(result_path)
    assert isinstance(img, Image.Image)

    # Should be larger than just the center image
    center_img = Image.open(test_image)
    assert img.size[0] > center_img.size[0]
    assert img.size[1] > center_img.size[1]


def test_create_qr_code_with_nonexistent_center_image(test_output, temp_dir):
    """Test that function handles nonexistent center image gracefully."""
    fake_path = str(temp_dir / "nonexistent.png")

    result_path = create_qr_code(
        "Test Data", str(test_output), center_image_path=fake_path
    )

    # Should still create QR code without center image
    assert Path(result_path).exists()

    img = Image.open(result_path)
    assert isinstance(img, Image.Image)


def test_prepare_center_image(test_image):
    """Test center image preparation."""
    qr_size = (200, 200)

    result_img = _prepare_center_image(
        str(test_image), qr_size, transparent_background=False
    )

    # Should be resized appropriately (about 1/5 of QR size)
    expected_max_size = min(qr_size) // 5
    assert max(result_img.size) <= expected_max_size


def test_prepare_center_image_with_transparent_background(test_image):
    """Test center image preparation with transparent background."""
    qr_size = (200, 200)

    result_img = _prepare_center_image(
        str(test_image), qr_size, transparent_background=True
    )

    # Should be larger due to white background
    original_img = Image.open(test_image)
    assert result_img.size[0] > original_img.size[0]
    assert result_img.size[1] > original_img.size[1]


@pytest.mark.parametrize(
    "scale,border",
    [
        (4, 2),
        (8, 4),
        (12, 6),
        (16, 8),
    ],
)
def test_different_scales_and_borders(temp_dir, scale, border):
    """Test QR code with different scales and borders."""
    output_path = temp_dir / f"qr_scale_{scale}_border_{border}.png"

    result_path = create_qr_code(
        "Test Data", str(output_path), scale=scale, border=border
    )

    assert Path(result_path).exists()

    img = Image.open(result_path)
    assert isinstance(img, Image.Image)
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_qr_code_with_different_data_types():
    """Test QR code generation with different types of data."""
    test_cases = [
        "Simple text",
        "https://github.com/user/repo",
        "mailto:test@example.com",
        "tel:+1234567890",
        "WIFI:T:WPA;S:MyNetwork;P:password123;;",
        "😀🎉 Unicode test! 中文",
    ]

    for i, data in enumerate(test_cases):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            result_path = create_qr_code(data, tmp.name)

            assert Path(result_path).exists()
            img = Image.open(result_path)
            assert isinstance(img, Image.Image)

            # Clean up
            Path(tmp.name).unlink()


def test_qr_code_with_all_options_combined(test_output, test_image):
    """Test QR code with all options combined."""
    result_path = create_qr_code(
        "Test with all options",
        str(test_output),
        center_image_path=str(test_image),
        dark_color="darkblue",
        light_color="lightgray",
        transparent_background=False,
        scale=10,
        border=5,
    )

    assert Path(result_path).exists()

    img = Image.open(result_path)
    assert isinstance(img, Image.Image)
    assert img.size[0] > 0
    assert img.size[1] > 0


@pytest.mark.parametrize("transparent", [True, False])
def test_qr_code_with_center_image_and_transparency(
    test_output, test_image, transparent
):
    """Test QR code with center image and different transparency settings."""
    result_path = create_qr_code(
        "Test transparency",
        str(test_output),
        center_image_path=str(test_image),
        transparent_background=transparent,
    )

    assert Path(result_path).exists()

    img = Image.open(result_path)
    assert isinstance(img, Image.Image)

    if transparent:
        # PNG with transparency can be various modes
        assert img.mode in ["RGBA", "LA", "P", "1"]


# Performance test (optional)
@pytest.mark.slow
def test_qr_code_performance():
    """Test that QR code generation is reasonably fast."""
    import time

    start_time = time.time()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        create_qr_code("Performance test", tmp.name)
        Path(tmp.name).unlink()

    end_time = time.time()

    # Should generate QR code in less than 2 seconds
    assert (end_time - start_time) < 2.0
