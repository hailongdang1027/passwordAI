#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from pattern_model import PatternFrequencyModel


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze aggregate password structure patterns from an authorized/synthetic dataset."
    )
    parser.add_argument("dataset", help="Text file with one sample per line")
    parser.add_argument("--top", type=int, default=20, help="Number of top patterns to show")
    parser.add_argument("--min-count", type=int, default=1, help="Minimum frequency for displayed patterns")
    parser.add_argument("--json", dest="json_path", help="Optional path for aggregate JSON summary")
    parser.add_argument("--csv", dest="csv_path", help="Optional path for aggregate pattern CSV")
    args = parser.parse_args()

    top = max(args.top, 1)
    min_count = max(args.min_count, 1)

    model = PatternFrequencyModel().fit_file(args.dataset)
    rows = model.top_patterns(limit=top, min_count=min_count)

    print(f"samples={model.total_samples}")
    print(f"unique_patterns={len(model.pattern_counts)}")
    print(f"average_length={model.average_length:.2f}")
    print(f"length_range={model.min_length}-{model.max_length}")
    print(f"top_coverage={model.coverage(limit=top, min_count=min_count):.2%}")
    print()
    print(f"{'probability':>11} {'count':>8}  pattern")
    for row in rows:
        print(f"{row.probability:>10.2%} {row.count:>8}  {row.pattern}")

    if args.json_path:
        output = Path(args.json_path)
        model.export_summary(output, limit=max(top, 100), min_count=min_count)
        print(f"\njson_summary={output.resolve()}")

    if args.csv_path:
        output = Path(args.csv_path)
        model.export_patterns_csv(output, limit=max(top, 100), min_count=min_count)
        print(f"csv_summary={output.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
