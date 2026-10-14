#!/usr/bin/env python3
"""Print the strategies detected in the mechanical generator source."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core_ai import analyze_core_source, format_core_analysis


def main() -> int:
    parser = argparse.ArgumentParser(description="Read mechanical password-generation strategies from Python source.")
    parser.add_argument(
        "source",
        nargs="?",
        default=str(Path(__file__).with_name("handle.py")),
        help="Core Python file (default: handle.py)",
    )
    parser.add_argument("--json", dest="json_path", help="Optional aggregate JSON report path")
    args = parser.parse_args()

    analysis = analyze_core_source(args.source)
    print(format_core_analysis(analysis))
    if args.json_path:
        payload = {
            "source_path": analysis.source_path,
            "source_sha256": analysis.source_sha256,
            "function_count": len(analysis.functions),
            "functions": list(analysis.functions),
            "strategies": [
                {
                    "key": strategy.key,
                    "label": strategy.label,
                    "description": strategy.description,
                    "evidence": list(strategy.evidence),
                    "confidence": strategy.confidence,
                }
                for strategy in analysis.strategies
            ],
        }
        Path(args.json_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\njson_report={Path(args.json_path).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
