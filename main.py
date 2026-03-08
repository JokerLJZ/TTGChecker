from __future__ import annotations

import argparse
import sys

from ttg_checker.config import load_config
from ttg_checker.service import CheckinService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TTG daily check-in automation")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to JSON config file (default: config.json)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(args.config)
    service = CheckinService(config)
    result = service.execute()
    print(result.message)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
