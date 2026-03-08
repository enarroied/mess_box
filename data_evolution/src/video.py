import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import get_video_resolution


_VIDEO_ENCODE_ARGS = [
    "-c:v",
    "libx264",
    "-preset",
    "medium",
    "-crf",
    "23",
    "-movflags",
    "+faststart",
    "-profile:v",
    "baseline",
    "-level",
    "3.1",
    "-pix_fmt",
    "yuv420p",
]

_SILENT_AUDIO_ARGS = [
    "-f",
    "lavfi",
    "-i",
    "anullsrc=r=44100:cl=stereo",
    "-c:a",
    "aac",
    "-b:a",
    "128k",
    "-shortest",
]

_AUDIO_ENCODE_ARGS = ["-c:a", "aac", "-b:a", "128k", "-shortest"]


def _get_dimensions(image_path: Path) -> tuple:
    with open(image_path, "rb") as f:
        f.seek(16)
        width, height = struct.unpack(">ii", f.read(8))
    width = (width // 2) * 2
    height = (height // 2) * 2
    return width, height


def _build_scale_filter(
    target_width: Optional[int], target_height: Optional[int], fallback_image: Path
) -> str:
    if target_width and target_height:
        return (
            f"scale={target_width}:{target_height}"
            f":force_original_aspect_ratio=decrease"
            f",pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"
        )
    width, height = _get_dimensions(fallback_image)
    return f"scale={width}:{height}"


def _write_concat_file(
    list_file: Path, image_paths: List[Path], duration: float
) -> None:
    with list_file.open("w") as f:
        for img in image_paths:
            f.write(f"file '{img.resolve().as_posix()}'\n")
            f.write(f"duration {duration}\n")
        # Repeat last frame so ffmpeg concat demuxer picks up its duration
        f.write(f"file '{image_paths[-1].resolve().as_posix()}'\n")


def make_video_from_images(
    image_paths: List[Path],
    output_path: Path,
    duration_per_frame: float = 0.2,
    fps: int = 30,
    target_width: int = None,
    target_height: int = None,
    audio_track: Optional[Path] = None,
) -> Path:
    if not image_paths:
        raise ValueError("No images provided")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    list_file = output_path.parent / "images.txt"
    _write_concat_file(list_file, image_paths, duration_per_frame)

    scale_filter = _build_scale_filter(target_width, target_height, image_paths[0])
    has_audio = audio_track and audio_track.exists()

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file)]

    if has_audio:
        cmd.extend(["-i", str(audio_track)])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])

    cmd.extend(["-vf", scale_filter, "-r", str(fps)])
    cmd.extend(_VIDEO_ENCODE_ARGS)
    cmd.extend(_AUDIO_ENCODE_ARGS)
    cmd.append(str(output_path))

    subprocess.run(cmd, check=True, capture_output=True)

    list_file.unlink()
    return output_path


def _image_scale_filter(width: int, height: int) -> str:
    return (
        f"scale={width}:{height}"
        f":force_original_aspect_ratio=decrease"
        f",pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    )


def _build_intro_outro_inputs(
    intro_image: Optional[Path],
    video_path: Path,
    outro_image: Optional[Path],
    target_width: int,
    target_height: int,
) -> tuple[list, list, int]:
    """
    Returns (ffmpeg_input_args, filter_parts, video_input_idx).
    """
    inputs = []
    filter_parts = []
    idx = 0

    if intro_image and intro_image.exists():
        inputs.extend(["-i", str(intro_image)])
        filter_parts.append(
            f"[{idx}:v]{_image_scale_filter(target_width, target_height)}[v{idx}]"
        )
        idx += 1

    inputs.extend(["-i", str(video_path)])
    filter_parts.append(f"[{idx}:v]setsar=1[v{idx}]")
    video_input_idx = idx
    idx += 1

    if outro_image and outro_image.exists():
        inputs.extend(["-i", str(outro_image)])
        filter_parts.append(
            f"[{idx}:v]{_image_scale_filter(target_width, target_height)}[v{idx}]"
        )
        idx += 1

    return inputs, filter_parts, video_input_idx, idx


class VideoBuilder:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.frames_dir = config["_frames_dir"]
        self.videos_dir = config["_videos_dir"]
        self.thumbnails_dir = config["_thumbnails_dir"]

    def create_video(
        self, frame_paths: List[Path], output_filename: str = "output.mp4"
    ) -> Path:
        self.videos_dir.mkdir(parents=True, exist_ok=True)

        output_path = self.videos_dir / output_filename
        fmt = self.config.get("format", "landscape")
        target_width, target_height = get_video_resolution(fmt)

        video_path = make_video_from_images(
            frame_paths,
            output_path,
            duration_per_frame=self.config.get("duration_per_frame", 0.2),
            fps=self.config.get("fps", 30),
            target_width=target_width,
            target_height=target_height,
            audio_track=self.config.get("audio_track"),
        )

        print(f"Video created: {video_path}")
        return video_path

    def add_intro_outro(
        self,
        video_path: Path,
        intro_image: Optional[Path] = None,
        intro_duration: float = 2.0,
        outro_image: Optional[Path] = None,
        outro_duration: float = 2.0,
    ) -> Path:
        if not intro_image and not outro_image:
            return video_path

        output_path = video_path.parent / f"with_intro_outro_{video_path.name}"

        fmt = self.config.get("format", "landscape")
        target_width, target_height = get_video_resolution(fmt)
        fps = self.config.get("fps", 30)
        audio_track = self.config.get("audio_track")
        has_audio = audio_track and audio_track.exists()

        inputs, filter_parts, video_input_idx, total_inputs = _build_intro_outro_inputs(
            intro_image, video_path, outro_image, target_width, target_height
        )

        concat_inputs = "".join(f"[v{i}]" for i in range(total_inputs))
        filter_complex = (
            f"{';'.join(filter_parts)};{concat_inputs}concat=n={total_inputs}:v=1:a=0"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-t",
            str(intro_duration) if intro_image else "1",
            "-framerate",
            str(fps),
        ] + inputs

        if has_audio:
            cmd.extend(["-i", str(audio_track)])

        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(_VIDEO_ENCODE_ARGS)

        if has_audio:
            cmd.extend(
                [
                    "-map",
                    f"[v{video_input_idx}]",
                    "-map",
                    f"{video_input_idx + 1}:a",
                ]
            )
            cmd.extend(_AUDIO_ENCODE_ARGS)
        else:
            cmd.extend(_SILENT_AUDIO_ARGS)

        if outro_image:
            cmd.extend(["-loop", "1", "-t", str(outro_duration)])

        cmd.append(str(output_path))

        subprocess.run(cmd, check=True, capture_output=True)

        print(f"Video with intro/outro created: {output_path}")
        return output_path

    def _save_thumbnail(self, intro_image: Path) -> Optional[Path]:
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

        if self.config.get("intro_image"):
            thumbnail_path = self.thumbnails_dir / "thumbnail.jpg"
            shutil.copy2(intro_image, thumbnail_path)
            print(f"Thumbnail saved: {thumbnail_path}")
            return thumbnail_path
        return None
