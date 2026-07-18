from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import analyse_document


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse a document with Repetita Gravity")
    parser.add_argument("document", type=Path)
    parser.add_argument("--context-limit", type=int, default=1_000_000)
    parser.add_argument("--safety-ratio", type=float, default=0.60)
    args = parser.parse_args()
    result = analyse_document(
        args.document.read_text(encoding="utf-8"),
        context_limit=args.context_limit,
        safety_ratio=args.safety_ratio,
    )
    print(json.dumps(result.to_dict(), indent=2, default=str))


if __name__ == "__main__":
    main()
