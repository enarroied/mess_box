#!/usr/bin/env python3
import argparse

from config import load_config, get_video_resolution
from dataset import DatasetHandler
from charts import ChartGenerator
from video import VideoBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Create motion chart videos from CSV data"
    )
    parser.add_argument(
        "config",
        type=str,
        help="Path to config.yaml file",
    )
    parser.add_argument(
        "--skip-frames",
        action="store_true",
        help="Skip frame generation (use existing frames)",
    )
    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="Skip video creation",
    )

    args = parser.parse_args()

    print(f"Loading config from: {args.config}")
    config = load_config(args.config)

    print("\nConfiguration:")
    print(f"  CSV: {config['csv_path']}")
    print(f"  Entity col: {config.get('entity_col', 'auto')}")
    print(f"  Time col: {config.get('time_col', 'auto')}")
    print(f"  Value col: {config.get('value_col', 'auto')}")
    print(f"  Format: {config['format']}")
    print(f"  Output: {config['_output_dir']}")

    width, height = get_video_resolution(config["format"])
    print(f"  Resolution: {width}x{height}")

    print("\n--- Loading dataset ---")
    dataset = DatasetHandler(config)
    print(f"  Entity column: {dataset.entity_col}")
    print(f"  Time column: {dataset.time_col}")
    print(f"  Value column: {dataset.value_col}")
    print(
        f"  Time values: {len(dataset.all_times)} ({min(dataset.all_times)} - {max(dataset.all_times)})"
    )

    frames_dir = config["_frames_dir"]

    if args.skip_frames:
        print("\n--- Skipping frame generation ---")
        frame_paths = sorted(frames_dir.glob("frame_*.png"))
        print(f"  Using {len(frame_paths)} existing frames")
    else:
        print("\n--- Generating frames ---")
        chart_gen = ChartGenerator(dataset, config)
        frame_paths = chart_gen.generate_frames(frames_dir)
        print(f"  Generated {len(frame_paths)} frames")

    if args.skip_video:
        print("\n--- Skipping video creation ---")
        return

    print("\n--- Creating video ---")
    video_builder = VideoBuilder(config)

    video_path = video_builder.create_video(frame_paths)

    intro_image = config.get("intro_image")
    intro_duration = config.get("intro_duration", 2.0)
    outro_image = config.get("outro_image")
    outro_duration = config.get("outro_duration", 2.0)

    if intro_image or outro_image:
        print("\n--- Adding intro/outro ---")
        final_video = video_builder.add_intro_outro(
            video_path,
            intro_image=intro_image,
            intro_duration=intro_duration,
            outro_image=outro_image,
            outro_duration=outro_duration,
        )
        print(f"  Final video: {final_video}")
    else:
        print(f"  Final video: {video_path}")

    print("\n--- Done! ---")


if __name__ == "__main__":
    main()
