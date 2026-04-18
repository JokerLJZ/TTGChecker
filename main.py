from __future__ import annotations

import argparse
import logging
import random
import sys
import time

from ttg_checker.config import load_config
from ttg_checker.service import CheckinService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TTG daily check-in (HTTP, no browser automation)")
    parser.add_argument("--config", default="config.json", help="Path to config JSON (default: config.json)")
    parser.add_argument(
        "--jitter-seconds",
        type=int,
        default=0,
        help="Sleep up to N random seconds before running (smooth out cron firing). 0 disables.",
    )
    return parser


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    configure_logging()
    args = build_parser().parse_args()

    if args.jitter_seconds > 0:
        delay = random.randint(0, args.jitter_seconds)
        logging.info("jitter sleep %ss", delay)
        time.sleep(delay)

    config = load_config(args.config)
    service = CheckinService(config)
    result = service.execute()
    print(result.message)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
