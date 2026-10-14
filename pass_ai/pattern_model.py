from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import csv
import json

COMMON_SEPARATORS = {"_", "-", ".", "@"}


def _char_class(ch: str) -> str:
    if ch.isalpha():
        return "alpha"
    if ch.isdigit():
        return "digit"
    return "special"


def _alpha_style(block: str) -> str:
    if block.islower():
        return "LOWER"
    if block.isupper():
        return "UPPER"
    if block[:1].isupper() and block[1:].islower():
        return "CAP"
    return "MIXED"


def _encode_block(kind: str, block: str) -> str:
    if kind == "alpha":
        return f"{_alpha_style(block)}{len(block)}"
    if kind == "digit":
        if len(block) == 4:
            try:
                year = int(block)
            except ValueError:
                year = -1
            if 1900 <= year <= 2099:
                return "YEAR4"
        return f"DIGIT{len(block)}"

    if len(block) == 1 and block in COMMON_SEPARATORS:
        names = {"_": "UNDERSCORE", "-": "HYPHEN", ".": "DOT", "@": "AT"}
        return f"SEP_{names[block]}"
    return f"SPECIAL{len(block)}"


def extract_block_pattern(password: str) -> str:
    """Convert a password into an aggregate structural pattern.

    The representation records structure rather than literal content.
    Example: ``Abc_2020`` -> ``CAP3+SEP_UNDERSCORE+YEAR4``.
    """
    if not password:
        return "EMPTY"

    blocks: list[tuple[str, str]] = []
    start = 0
    current = _char_class(password[0])
    for index, ch in enumerate(password[1:], start=1):
        kind = _char_class(ch)
        if kind != current:
            blocks.append((current, password[start:index]))
            start = index
            current = kind
    blocks.append((current, password[start:]))

    return "+".join(_encode_block(kind, block) for kind, block in blocks)


@dataclass(frozen=True)
class PatternStat:
    pattern: str
    count: int
    probability: float


@dataclass(frozen=True)
class LengthStat:
    length: int
    count: int
    probability: float


class PatternFrequencyModel:
    """Frequency model for studying password-structure prevalence.

    Raw input strings are never retained. The model stores only aggregate
    structural-pattern counts and aggregate length counts.
    """

    def __init__(self) -> None:
        self.pattern_counts: Counter[str] = Counter()
        self.length_counts: Counter[int] = Counter()
        self.total_samples = 0
        self.total_length = 0

    def fit(self, passwords: Iterable[str]) -> "PatternFrequencyModel":
        self.pattern_counts.clear()
        self.length_counts.clear()
        self.total_samples = 0
        self.total_length = 0

        for raw in passwords:
            password = raw.rstrip("\r\n")
            if not password:
                continue
            self.pattern_counts[extract_block_pattern(password)] += 1
            self.length_counts[len(password)] += 1
            self.total_samples += 1
            self.total_length += len(password)
        return self

    def fit_file(self, path: str | Path, encoding: str = "utf-8") -> "PatternFrequencyModel":
        with open(path, "r", encoding=encoding, errors="ignore") as handle:
            return self.fit(handle)

    @property
    def average_length(self) -> float:
        if self.total_samples <= 0:
            return 0.0
        return self.total_length / self.total_samples

    @property
    def min_length(self) -> int:
        return min(self.length_counts) if self.length_counts else 0

    @property
    def max_length(self) -> int:
        return max(self.length_counts) if self.length_counts else 0

    def probability(self, pattern_or_password: str, *, is_pattern: bool = False) -> float:
        if self.total_samples <= 0:
            return 0.0
        pattern = pattern_or_password if is_pattern else extract_block_pattern(pattern_or_password)
        return self.pattern_counts.get(pattern, 0) / self.total_samples

    def top_patterns(self, limit: int = 20, min_count: int = 1) -> list[PatternStat]:
        if limit <= 0 or self.total_samples <= 0:
            return []
        min_count = max(int(min_count), 1)
        rows: list[PatternStat] = []
        for pattern, count in self.pattern_counts.most_common():
            if count < min_count:
                continue
            rows.append(PatternStat(pattern, count, count / self.total_samples))
            if len(rows) >= limit:
                break
        return rows

    def length_distribution(self) -> list[LengthStat]:
        if self.total_samples <= 0:
            return []
        return [
            LengthStat(length, count, count / self.total_samples)
            for length, count in sorted(self.length_counts.items())
        ]

    def coverage(self, limit: int = 20, min_count: int = 1) -> float:
        return sum(row.probability for row in self.top_patterns(limit=limit, min_count=min_count))

    def summary(self, limit: int = 100, min_count: int = 1) -> dict:
        return {
            "total_samples": self.total_samples,
            "unique_patterns": len(self.pattern_counts),
            "average_length": self.average_length,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "coverage": self.coverage(limit=limit, min_count=min_count),
            "length_distribution": [
                {
                    "length": row.length,
                    "count": row.count,
                    "probability": row.probability,
                }
                for row in self.length_distribution()
            ],
            "patterns": [
                {
                    "pattern": row.pattern,
                    "count": row.count,
                    "probability": row.probability,
                }
                for row in self.top_patterns(limit=limit, min_count=min_count)
            ],
        }

    def export_summary(self, path: str | Path, limit: int = 100, min_count: int = 1) -> None:
        Path(path).write_text(
            json.dumps(self.summary(limit=limit, min_count=min_count), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def export_patterns_csv(self, path: str | Path, limit: int = 100, min_count: int = 1) -> None:
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["pattern", "count", "probability"])
            for row in self.top_patterns(limit=limit, min_count=min_count):
                writer.writerow([row.pattern, row.count, f"{row.probability:.8f}"])
