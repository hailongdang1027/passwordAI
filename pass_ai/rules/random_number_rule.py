"""Optional random digits rule; independent of the mechanical generator."""

import random
from typing import Any, Mapping

from handle import normalize_word, parse_vietnamese_name


RULE_NAME = "GHÉP_SỐ_NGẪU_NHIÊN"
DEFAULT_PARAMS = {
    "min_digits": 2,
    "max_digits": 4,
    "count": 10,
    "position": "both",
}


def validate_params(params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Validate both GUI values and programmatic calls before generating."""
    values = dict(DEFAULT_PARAMS)
    if params:
        unknown = set(params) - set(DEFAULT_PARAMS)
        if unknown:
            raise ValueError(f"Tham số không hỗ trợ: {', '.join(sorted(unknown))}")
        values.update(params)

    for key, maximum in (("min_digits", 8), ("max_digits", 8), ("count", 100)):
        value = values[key]
        if isinstance(value, str):
            try:
                value = int(value.strip())
            except ValueError:
                raise ValueError(f"{key} phải là số nguyên từ 1 đến {maximum}.") from None
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError(f"{key} phải là số nguyên từ 1 đến {maximum}.")
        values[key] = value

    if values["min_digits"] > values["max_digits"]:
        raise ValueError("Độ dài số từ (min_digits) không được lớn hơn đến (max_digits).")
    if values["position"] not in ("prefix", "suffix", "both"):
        raise ValueError("position phải là prefix (trước), suffix (sau) hoặc both (cả hai).")
    return values


def profile_words(profile: Mapping[str, str]) -> set[str]:
    """Reuse name normalization, without invoking the mechanical generator."""
    words = set()
    for field in ("fullname", "relative_name", "child_name"):
        info = parse_vietnamese_name(profile.get(field) or "")
        if info:
            words.update(info["variants"])
    for field in ("hometown", "company"):
        word = "".join(normalize_word(profile.get(field) or "").split()).lower()
        if word:
            words.add(word)
    return words


class RandomNumberRule:
    """Add unique digit strings before/after each nonempty profile word.

    count applies to each word and each digit width. Leading zeroes are kept.
    SystemRandom uses fresh OS randomness; the core's configured seed is not
    read or changed. An injected RNG is supported for reproducible tests.
    """

    def __init__(self, *, rng=None, **params):
        self.params = validate_params(params)
        self.rng = rng if rng is not None else random.SystemRandom()

    def generate(self, profile: Mapping[str, str], min_length: int, max_length: int) -> set[str]:
        results = set()
        p = self.params
        for word in sorted(profile_words(profile)):
            for width in range(p["min_digits"], p["max_digits"] + 1):
                # Skip impossible lengths before drawing numbers.
                if not min_length <= len(word) + width <= max_length:
                    continue
                space = 10 ** width
                for number in self.rng.sample(range(space), min(p["count"], space)):
                    digits = str(number).zfill(width)
                    if p["position"] in ("prefix", "both"):
                        results.add(digits + word)
                    if p["position"] in ("suffix", "both"):
                        results.add(word + digits)
        return results
