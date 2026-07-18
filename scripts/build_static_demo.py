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
    release = payload["safe_pass"]
    formal = release["global_verification"]
    semantic = release["global_semantic_verification"]
    release_invariants = {
        "certification eligible": release["certification"]["eligible"],
        "certification label": release["certification"]["label"] == "VERIFIED BY REPETITA GRAVITY",
        "ledger fully covered": formal["ledger_coverage"] == 1,
        "zero unresolved occurrences": formal["unresolved_occurrences"] == 0,
        "zero hard-anchor losses": not formal["missing_hard_anchors"],
        "semantic gate passed": semantic["status"] == "PASSED",
        "at least one committed repair": bool(release["transactions"]),
    }
    failed = [name for name, passed in release_invariants.items() if not passed]
    if failed:
        raise RuntimeError(
            "The static demo cannot be published; failed release gates: " + ", ".join(failed)
        )
    (OUTPUT / "demo-data.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    print(
        f"Built certified static demo in {OUTPUT}: "
        f"{formal['accounted_unit_count']}/{formal['original_unit_count']} units, "
        f"{formal['unresolved_occurrences']} unresolved, semantic gate {semantic['status']}"
    )


if __name__ == "__main__":
    main()
