import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from crossroads.app import run
from crossroads.runtime_config import resolve_runtime_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CrossRoadsAI static intersection app.")
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Optional frame cap for smoke runs in non-interactive environments.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional path to a YAML simulation config. Defaults to config/simulation.yaml when present.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        runtime_config = resolve_runtime_config(config_path=args.config)
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(2) from exc
    run(max_frames=args.max_frames, runtime_config=runtime_config)
