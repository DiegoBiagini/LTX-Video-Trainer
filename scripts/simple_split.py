#!/usr/bin/env python3

"""
A simpler version of split_scenes.py for time-based video splitting.
"""

import cv2
import typer
from pathlib import Path
import os
import re

app = typer.Typer(no_args_is_help=True, help="Split video into fixed-length chunks.")

def split_video_by_time(
    video_path: Path,
    output_dir: Path,
    frames_per_split: int,
):
    """
    Splits a single video into multiple smaller clips.
    If the final chunk has fewer than frames_per_split frames,
    it is deleted.
    """
    video = cv2.VideoCapture(str(video_path))
    if not video.isOpened():
        print(f"Error: Could not open video {video_path}")
        return

    fps    = video.get(cv2.CAP_PROP_FPS)
    w      = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    h      = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    frame_count    = 0
    split_count    = 0
    video_writer   = None
    last_out_path  = None
    frames_in_split = 0

    while True:
        ret, frame = video.read()
        if not ret:
            break

        # start a new split
        if frame_count % frames_per_split == 0:
            # close the old one
            if video_writer is not None:
                video_writer.release()

            start = split_count * frames_per_split
            end   = start + (frames_per_split-1)
            name  = f"{video_path.stem}_{start}_{end}{video_path.suffix}"
            out   = output_dir / name

            print(f"Creating new split: {out}")
            video_writer   = cv2.VideoWriter(str(out), fourcc, fps, (w, h))
            last_out_path  = out
            frames_in_split = 0
            split_count   += 1

        video_writer.write(frame)
        frame_count    += 1
        frames_in_split += 1

    # clean up
    if video_writer is not None:
        video_writer.release()
    video.release()

    # if the last split was incomplete, delete it
    if frames_in_split < frames_per_split and last_out_path is not None:
        print(f"Deleting incomplete split {last_out_path} ({frames_in_split}/{frames_per_split} frames)")
        os.remove(last_out_path)

def load_full_video_from_split(first_split_path: Path):
    """
    Loads a full video by finding and concatenating all its split parts.
    It identifies parts based on the filename of the first split.
    """
    if not first_split_path.exists():
        print(f"Error: The file {first_split_path} does not exist.")
        return

    directory = first_split_path.parent
    
    # Extract base name correctly, even if the original name had underscores
    match = re.match(r'(.+)_(\d+)_(\d+)', first_split_path.stem)
    if not match:
        print(f"Error: Filename '{first_split_path.name}' does not match the expected pattern 'name_start_end.ext'")
        return
    base_name = match.group(1)

    split_files = sorted(
        [p for p in directory.glob(f"{base_name}_*.{first_split_path.suffix.lstrip('.')}") if re.match(r'(.+)_(\d+)_(\d+)', p.stem)],
        key=lambda p: int(p.stem.split('_')[-2])
    )

    print(f"Found {len(split_files)} split files for base name '{base_name}'.")

    for split_file in split_files:
        print(f"Processing {split_file.name}...")
        video = cv2.VideoCapture(str(split_file))
        if not video.isOpened():
            print(f"Warning: Could not open split file {split_file}, skipping.")
            continue
        
        while True:
            ret, frame = video.read()
            if not ret:
                break
            yield frame
        video.release()

@app.command()
def split(
    input_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=True, help="Path to the video file or directory of videos to split."),
    output_dir: Path = typer.Argument(..., file_okay=False, dir_okay=True, help="Directory to save the split video clips."),
    frames_per_split: int = typer.Option(150, "--frames", "-f", help="Number of frames per split."),
):
    """Splits a video or all videos in a directory into smaller clips."""
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    if input_path.is_dir():
        for video_file in input_path.glob('*'):
            if video_file.is_file() and video_file.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                print(f"Processing video: {video_file.name}")
                # Create a subdirectory for each video's splits
                video_output_dir = output_dir
                if not video_output_dir.exists():
                    video_output_dir.mkdir(parents=True)
                split_video_by_time(video_file, video_output_dir, frames_per_split)
    elif input_path.is_file():
        split_video_by_time(input_path, output_dir, frames_per_split)
    
    print("Video splitting complete.")

@app.command()
def reconstruct(
    first_split_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, help="Path to the first split of the video."),
    output_path: Path = typer.Argument(..., file_okay=False, dir_okay=False, help="Path to save the reconstructed video."),
):
    """Reconstructs a full video from its split parts."""
    
    # Get properties from the first video clip
    video = cv2.VideoCapture(str(first_split_path))
    if not video.isOpened():
        typer.echo(f"Error: Could not open video file {first_split_path}", err=True)
        raise typer.Exit(code=1)
        
    fps = video.get(cv2.CAP_PROP_FPS)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video.release()

    # Create VideoWriter for the output
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True)
    video_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    frame_generator = load_full_video_from_split(first_split_path)
    
    for frame in frame_generator:
        video_writer.write(frame)

    video_writer.release()
    typer.echo(f"Reconstructed video saved to {output_path}")


if __name__ == "__main__":
    app()