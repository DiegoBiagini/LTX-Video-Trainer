import os
import glob
import json
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="Scan a folder (recursively) for .mp4 files "
                    "and write out a dataset.json with a fixed caption."
    )
    parser.add_argument(
        "input_folder",
        help="Path to the input folder where .mp4 files live and where dataset.json will be written"
    )
    args = parser.parse_args()
    input_folder = args.input_folder

    # you can of course make this a CLI arg as well
    caption = (
        "In the video, Mario is seen running across a level with a clear "
        "blue sky and green hills in the background. He jumps over obstacles "
        "and collects coins while avoiding enemies like Goombas."
    )

    # build a recursive glob pattern under the provided folder
    pattern = os.path.join(input_folder, "**", "*.mp4")
    mp4_files = glob.glob(pattern, recursive=True)

    out = [
        {
            "caption": caption,
            "media_path": Path(fp).name
        }
        for fp in mp4_files
    ]

    # ensure the folder exists
    Path(input_folder).mkdir(parents=True, exist_ok=True)

    # write the JSON to dataset.json inside input_folder
    output_path = Path(input_folder) / "dataset.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Found {len(mp4_files)} .mp4 files. Wrote {output_path}")

if __name__ == "__main__":
    main()