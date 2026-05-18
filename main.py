import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from crossroads.app import run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CrossRoadsAI static intersection app.")
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Optional frame cap for smoke runs in non-interactive environments.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(max_frames=args.max_frames)
