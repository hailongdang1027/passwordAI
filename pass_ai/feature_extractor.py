"""Generic, label-agnostic password features for defensive strength assessment.

Features are measurements, never a manually weighted password score.
Do not put the literal password in logs, reports or exported artifacts.
"""
from __future__ import annotations

from password_utils import calculate_entropy

FEATURE_NAMES = (
    "length",
    "lowercase_ratio",
    "uppercase_ratio",
    "digit_ratio",
    "symbol_ratio",
    "unique_char_ratio",
    "longest_repeat_run",
    "longest_digit_run",
    "longest_alpha_run",
    "shannon_entropy",
    "character_class_count",
)

FEATURE_LABELS = {
    "length": "Độ dài",
    "lowercase_ratio": "Tỷ lệ chữ thường",
    "uppercase_ratio": "Tỷ lệ chữ hoa",
    "digit_ratio": "Tỷ lệ chữ số",
    "symbol_ratio": "Tỷ lệ ký tự khác chữ/số",
    "unique_char_ratio": "Tỷ lệ ký tự phân biệt",
    "longest_repeat_run": "Chuỗi ký tự trùng liên tiếp dài nhất",
    "longest_digit_run": "Chuỗi chữ số liên tiếp dài nhất",
    "longest_alpha_run": "Chuỗi chữ liên tiếp dài nhất",
    "shannon_entropy": "Entropy Shannon đo được",
    "character_class_count": "Số nhóm ký tự",
}


def _longest_run(password: str, predicate) -> int:
    current = longest = 0
    for char in password:
        current = current + 1 if predicate(char) else 0
        longest = max(longest, current)
    return longest


def extract_features(password: str) -> list[float]:
    """Produce a fixed-length numeric vector without retaining input text."""
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    length = len(password)
    if length == 0:
        raise ValueError("Không thể đánh giá mật khẩu trống.")

    lower = sum(c.islower() for c in password)
    upper = sum(c.isupper() for c in password)
    digits = sum(c.isdigit() for c in password)
    symbols = length - lower - upper - digits
    repeats = 0
    prev = None
    current = 0
    for c in password:
        current = current + 1 if c == prev else 1
        prev = c
        repeats = max(repeats, current)

    return [
        float(length),
        lower / length,
        upper / length,
        digits / length,
        symbols / length,
        len(set(password)) / length,
        float(repeats),
        float(_longest_run(password, str.isdigit)),
        float(_longest_run(password, str.isalpha)),
        calculate_entropy(password),
        float(sum(bool(x) for x in (lower, upper, digits, symbols))),
    ]
