import ffmpeg
from pathlib import Path
from typing import Dict, Any, Optional, List
import shutil


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
    with list_file.open("w") as f:
        for img in image_paths:
            f.write(f"file '{img.resolve().as_posix()}'\n")
            f.write(f"duration {duration_per_frame}\n")

        f.write(f"file '{image_paths[-1].resolve().as_posix()}'\n")

    if target_width and target_height:
        scale_filter = f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"
    else:
        width, height = _get_dimensions(image_paths[0])
        scale_filter = f"scale={width}:{height}"

    import subprocess

    has_audio = audio_track and audio_track.exists()

    cmd = ["ffmpeg", "-y"]

    if has_audio:
        cmd.extend(
            ["-f", "concat", "-safe", "0", "-i", str(list_file), "-i", str(audio_track)]
        )
    else:
        cmd.extend(
            [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=stereo",
            ]
        )

    cmd.extend(
        [
            "-vf",
            scale_filter,
            "-r",
            str(fps),
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
    )

    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", "128k", "-shortest"])
    else:
        cmd.extend(["-c:a", "aac", "-b:a", "128k", "-shortest"])

    cmd.append(str(output_path))

    subprocess.run(cmd, check=True, capture_output=True)

    list_file.unlink()
    return output_path


def _get_dimensions(image_path: Path) -> tuple:
    import struct

    with open(image_path, "rb") as f:
        f.seek(16)
        width, height = struct.unpack(">ii", f.read(8))

    width = (width // 2) * 2
    height = (height // 2) * 2
    return width, height


from config import get_video_resolution


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

        duration = self.config.get("duration_per_frame", 0.2)
        fps = self.config.get("fps", 30)

        fmt = self.config.get("format", "landscape")
        target_width, target_height = get_video_resolution(fmt)

        audio_track = self.config.get("audio_track")

        video_path = make_video_from_images(
            frame_paths,
            output_path,
            duration_per_frame=duration,
            fps=fps,
            target_width=target_width,
            target_height=target_height,
            audio_track=audio_track,
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

        import subprocess

        inputs = []
        filter_parts = []
        input_idx = 0

        if intro_image and intro_image.exists():
            inputs.extend(["-i", str(intro_image)])
            filter_parts.append(
                f"[{input_idx}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{input_idx}]"
            )
            input_idx += 1
            self._save_thumbnail(intro_image)

        inputs.extend(["-i", str(video_path)])
        filter_parts.append(f"[{input_idx}:v]setsar=1[v{input_idx}]")
        video_input_idx = input_idx
        input_idx += 1

        if outro_image and outro_image.exists():
            inputs.extend(["-i", str(outro_image)])
            filter_parts.append(
                f"[{input_idx}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{input_idx}]"
            )
            input_idx += 1

        concat_list = "".join([f"[v{i}]" for i in range(input_idx)])
        filter_complex = (
            f"{';'.join(filter_parts)};{concat_list}concat=n={input_idx}:v=1:a=0"
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

        video_output_args = [
            "-filter_complex",
            filter_complex,
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

        if has_audio:
            cmd.extend(
                video_output_args
                + [
                    "-map",
                    f"[v{video_input_idx}]",
                    "-map",
                    f"{video_input_idx + 1}:a",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-shortest",
                ]
            )
        else:
            cmd.extend(
                video_output_args
                + [
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
            )

        if outro_image:
            cmd.extend(
                [
                    "-loop",
                    "1",
                    "-t",
                    str(outro_duration),
                ]
            )

        cmd.append(str(output_path))

        subprocess.run(cmd, check=True, capture_output=True)

        print(f"Video with intro/outro created: {output_path}")
        return output_path

    def _save_thumbnail(self, intro_image: Path) -> Path:
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

        if self.config.get("intro_image"):
            thumbnail_path = self.thumbnails_dir / "thumbnail.jpg"
            shutil.copy2(intro_image, thumbnail_path)
            print(f"Thumbnail saved: {thumbnail_path}")
            return thumbnail_path
        return None
