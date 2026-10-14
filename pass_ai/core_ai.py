"""Static AST analysis of the legacy generator; no password scoring or ranking."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path



@dataclass(frozen=True)
class CoreStrategy:
    key: str
    label: str
    description: str
    evidence: tuple[str, ...]
    confidence: float


@dataclass(frozen=True)
class CoreAnalysis:
    source_path: str
    source_sha256: str
    functions: tuple[str, ...]
    strategies: tuple[CoreStrategy, ...]


_STRATEGY_SIGNATURES = (
    {
        "key": "NORMALIZE_CASE",
        "label": "Chuẩn hóa và biến thể hoa/thường",
        "description": "Bỏ dấu, bỏ khoảng trắng rồi tạo thường, hoa và viết hoa đầu từ.",
        "terms": ("normalize_word", ".upper(", ".lower(", ".title("),
    },
    {
        "key": "BOUNDARY_SPECIAL",
        "label": "Ký tự đặc biệt ở biên",
        "description": "Thêm ký tự cấu hình vào đầu hoặc cuối chuỗi cơ sở.",
        "terms": ("boundary_chars", "spec + base_str", "base_str + spec"),
    },
    {
        "key": "COMMON_PREFIX_SUFFIX",
        "label": "Tiền tố và hậu tố cấu hình",
        "description": "Áp dụng prefixes/suffixes từ cấu hình patterns.",
        "terms": ("apply_common_patterns", "suffixes", "prefixes"),
    },
    {
        "key": "NAME_VARIANTS",
        "label": "Biến thể tên",
        "description": "Tách họ, tên đệm, tên và ghép các thứ tự tên phổ biến.",
        "terms": ("parse_vietnamese_name", "given_full", "surname", "variants"),
    },
    {
        "key": "DATE_VARIANTS",
        "label": "Biến thể ngày tháng",
        "description": "Dùng năm, năm hai chữ số, ngày-tháng và các khối ngày hợp lệ.",
        "terms": ("generate_date_variants", "birthdate", "relative_birth", "child_birth"),
    },
    {
        "key": "SEPARATOR_COMBINATION",
        "label": "Ghép bằng dấu phân cách",
        "description": "Ghép các khối bằng _, -, @ và các dấu cấu hình khác.",
        "terms": ("separator_chars", "for sep in", "process_and_add(sp + sep"),
    },
    {
        "key": "COMPANY_HOMETOWN",
        "label": "Công ty và quê quán",
        "description": "Đưa company/hometown vào các chuỗi cơ sở và tổ hợp với tên/ngày.",
        "terms": ("company", "hometown", "base_val", "main_names"),
    },
    {
        "key": "CROSS_FAMILY_DATES",
        "label": "Ghép chéo ngày trong gia đình",
        "description": "Ghép các năm/ngày của nhiều trường thông tin thành khối chéo.",
        "terms": ("generate_cross_family_dates", "cross_dates", "itertools.permutations"),
    },
    {
        "key": "OUTPUT_FILTER",
        "label": "Lọc độ dài và hình thái",
        "description": "Loại chuỗi vượt độ dài, lặp dấu phân cách hoặc có dấu liền nhau.",
        "terms": ("password_filter", "count_separators", "wcfrom", "wcto"),
    },
)


class _CoreVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.functions: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.functions.append(node.name)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


def analyze_core_source(path: str | Path) -> CoreAnalysis:
    """Read a local core source file and return aggregate strategy evidence."""
    source_path = Path(path)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    visitor = _CoreVisitor()
    visitor.visit(tree)

    strategies: list[CoreStrategy] = []
    for signature in _STRATEGY_SIGNATURES:
        evidence = tuple(term for term in signature["terms"] if term in source)
        confidence = round(len(evidence) / len(signature["terms"]), 3)
        if confidence >= 0.5:
            strategies.append(
                CoreStrategy(
                    key=signature["key"],
                    label=signature["label"],
                    description=signature["description"],
                    evidence=evidence,
                    confidence=confidence,
                )
            )

    return CoreAnalysis(
        source_path=str(source_path.resolve()),
        source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        functions=tuple(visitor.functions),
        strategies=tuple(strategies),
    )


def format_core_analysis(analysis: CoreAnalysis) -> str:
    """Render a safe, compact explanation suitable for the GUI."""
    lines = [
        f"Nguồn: {Path(analysis.source_path).name}",
        f"Hàm đọc được: {len(analysis.functions)} | Chiến lược: {len(analysis.strategies)}",
        f"SHA-256 mã nguồn: {analysis.source_sha256[:16]}…",
        "",
    ]
    for index, strategy in enumerate(analysis.strategies, start=1):
        evidence = ", ".join(strategy.evidence[:4])
        lines.append(f"{index}. {strategy.label} ({strategy.confidence:.0%})")
        lines.append(f"   {strategy.description}")
        lines.append(f"   Dấu hiệu mã: {evidence}")
    return "\n".join(lines)
