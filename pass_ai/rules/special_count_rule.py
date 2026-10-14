"""Optional final transformation: exact, selectable numbers of punctuation.

This samples bounded sets of variants, not every possible insertion. Local,
per-base RNG seeds make repeats reproducible without changing global RNG state.
"""
import hashlib
import math
import random
import string
from itertools import combinations_with_replacement, product

RULE_NAME = "SỐ_KÝ_TỰ_ĐẶC_BIỆT"
DEFAULT_PARAMS = {
    "counts": [1],
    "characters": "@!#$_-.*&%+",
    "position": "prefer_edges",
    "samples": 24,
}


def count_specials(value):
    """Count occurrences, not distinct symbols. Underscores also count."""
    return sum(not char.isalnum() for char in value)


def _integer(value, name, low, high):
    if isinstance(value, str):
        try:
            value = int(value.strip())
        except ValueError:
            pass
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} phải là số nguyên từ {low} đến {high}.")
    return value


def validate_params(params=None):
    values = dict(DEFAULT_PARAMS)
    if params:
        unknown = set(params) - set(values)
        if unknown:
            raise ValueError(f"Tham số không hỗ trợ: {', '.join(sorted(unknown))}")
        values.update(params)
    counts = values["counts"]
    if not isinstance(counts, (list, tuple)) or not counts:
        raise ValueError("Chọn ít nhất một số lượng ký tự đặc biệt; dùng nút + để thêm nhóm.")
    values["counts"] = sorted({_integer(n, "Số ký tự đặc biệt", 0, 64) for n in counts})
    chars = values["characters"]
    if not isinstance(chars, str) or not chars or any(c not in string.punctuation for c in chars):
        raise ValueError("Tập ký tự chỉ được chứa dấu như @!#$_-, không chứa chữ, số hoặc khoảng trắng.")
    values["characters"] = "".join(dict.fromkeys(chars))
    if values["position"] not in ("prefer_edges", "any", "edges"):
        raise ValueError("Vị trí phải là prefer_edges, any hoặc edges.")
    values["samples"] = _integer(values["samples"], "Số mẫu mỗi nhóm/chuỗi nền", 1, 100)
    return values


def _render(base, gaps, symbols):
    blocks = [""] * (len(base) + 1)
    for gap, symbol in zip(gaps, symbols):
        blocks[gap] += symbol
    return "".join(blocks[i] + char for i, char in enumerate(base)) + blocks[-1]


def _sample_indices(rng, population, limit):
    # range/sample has a platform length limit; large count selections can
    # exceed it even though only a few variants are requested.
    limit = min(population, limit)
    if population <= 10000:
        return rng.sample(range(population), limit)
    selected = set()
    while len(selected) < limit:
        selected.add(rng.randrange(population))
    return sorted(selected)


def _edge_variants(base, count, chars, limit, rng):
    codes = len(chars) ** count
    results = set()
    for index in _sample_indices(rng, (count + 1) * codes, limit):
        prefix_count, code = divmod(index, codes)
        symbols = []
        for _ in range(count):
            code, digit = divmod(code, len(chars))
            symbols.append(chars[digit])
        results.add("".join(symbols[:prefix_count]) + base + "".join(symbols[prefix_count:]))
    return results


def _position_variants(base, count, chars, limit, rng, *, require_internal=False):
    if limit <= 0 or (require_internal and len(base) < 2):
        return set()
    layouts = math.comb(len(base) + count, count)
    population = (layouts - (count + 1) if require_internal else layouts) * len(chars) ** count
    limit = min(limit, population)
    if population <= 5000:
        # Exhaust small spaces so single-symbol/count=1 requests can cover
        # every valid gap rather than losing variants to repeated draws.
        candidates = []
        for gaps in combinations_with_replacement(range(len(base) + 1), count):
            if require_internal and not any(0 < gap < len(base) for gap in gaps):
                continue
            for symbols in product(chars, repeat=count):
                candidates.append(_render(base, gaps, symbols))
        return set(rng.sample(candidates, limit))
    results = set()
    for _ in range(max(100, limit * 100)):
        gaps = sorted(rng.randrange(len(base) + 1) for _ in range(count))
        if require_internal and not any(0 < gap < len(base) for gap in gaps):
            continue
        results.add(_render(base, gaps, [rng.choice(chars) for _ in range(count)]))
        if len(results) >= limit:
            break
    return results


class SpecialCountRule:
    def __init__(self, **params):
        self.params = validate_params(params)

    def apply(self, passwords, min_length, max_length):
        # Rebuild punctuation from the letter/digit skeleton: existing marks
        # must not be added on top of the requested total. Preserve case/order.
        bases = {"".join(c for c in value if c.isalnum()) for value in passwords}
        bases.discard("")
        results = set()
        p = self.params
        for base in sorted(bases):
            for count in p["counts"]:
                if not min_length <= len(base) + count <= max_length:
                    continue
                if count == 0:
                    results.add(base)
                    continue
                seed = hashlib.sha256(f"{base}\0{count}\0{p['characters']}\0{p['position']}".encode()).digest()
                rng = random.Random(seed)
                if p["position"] == "edges":
                    variants = _edge_variants(base, count, p["characters"], p["samples"], rng)
                elif p["position"] == "any":
                    variants = _position_variants(base, count, p["characters"], p["samples"], rng)
                else:
                    target = math.ceil(p["samples"] * 0.7)
                    variants = _edge_variants(base, count, p["characters"], target, rng)
                    variants.update(_position_variants(
                        base, count, p["characters"], p["samples"] - len(variants), rng,
                        require_internal=True,
                    ))
                results.update(variants)
        return results
