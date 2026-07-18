from __future__ import annotations

import json
import shutil
from pathlib import Path

from repetita.api import analyse_payload, safe_pass_payload


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
SAMPLE = ROOT / "sample-data" / "adversarial-professional.md"
OUTPUT = ROOT / "_site"


def main() -> None:
    text = SAMPLE.read_text(encoding="utf-8")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    shutil.copytree(FRONTEND, OUTPUT)
    payload = {
        "sample": text,
        "analyse": analyse_payload({"text": text}),
        "safe_pass": safe_pass_payload({"text": text}),
    }
    if not payload["safe_pass"]["certification"]["eligible"]:
        raise RuntimeError("The static demo cannot be published without passing certification")
    (OUTPUT / "demo-data.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built certified static demo in {OUTPUT}")


if __name__ == "__main__":
    main()
