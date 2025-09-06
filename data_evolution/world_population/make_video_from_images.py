import ffmpeg
from pathlib import Path

def make_video_from_images(
    folder="./results", output="./videos/world_population.mp4", duration=0.2
):
    """
    Turns all PNG images in a folder into a video using ffmpeg-python.

    Args:
        folder (str): Folder with PNG images.
        output (str): Output video filename.
        duration (int or float): Seconds per image.
    """
    folder = Path(folder).resolve()
    output = Path(output).resolve()

    files = sorted([f for f in folder.iterdir() if f.suffix.lower() == ".png"])

    if not files:
        raise ValueError(f"No PNG files found in {folder}")

    list_file = folder / "images.txt"
    with list_file.open("w") as f:
        for img in files:
            f.write(f"file '{img.resolve().as_posix()}'\n")
            f.write(f"duration {duration}\n")

        # Ensure last frame is shown (ffmpeg quirk: needs last file repeated)
        f.write(f"file '{files[-1].resolve().as_posix()}'\n")

    (
        ffmpeg.input(str(list_file), format="concat", safe=0)
        .output(
            str(output),
            vcodec="libx264",
            pix_fmt="yuv420p",
            vf="scale=trunc(iw/2)*2:trunc(ih/2)*2",
        )
        .run(overwrite_output=True)
    )

    list_file.unlink()