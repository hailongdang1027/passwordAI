from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import handle

from .random_number_rule import RULE_NAME, RandomNumberRule, validate_params
from .registry import RULE_REGISTRY
from .special_count_rule import RULE_NAME as SPECIAL_RULE_NAME, SpecialCountRule, validate_params as validate_special_params


class RuleValidationError(ValueError):
    pass


@dataclass
class ValidatedRule:
    name: str
    params: dict[str, Any]


class RuleExecutor:
    """Validate and execute only the rules explicitly selected in the GUI."""

    def __init__(self, registry=None):
        self.registry = registry or RULE_REGISTRY

    def validate_rule(self, name: str, params: Mapping[str, Any] | None = None) -> ValidatedRule:
        if name not in self.registry:
            raise RuleValidationError(f"Rule không tồn tại: {name}")

        definition = self.registry[name]
        if not definition.implemented:
            raise RuleValidationError(f"Rule chưa được triển khai: {name}")

        merged = dict(definition.parameter_defaults)
        if params:
            merged.update(dict(params))
        if name == RULE_NAME:
            try:
                merged = validate_params(merged)
            except ValueError as exc:
                raise RuleValidationError(str(exc)) from exc
        elif name == SPECIAL_RULE_NAME:
            try:
                merged = validate_special_params(merged)
            except ValueError as exc:
                raise RuleValidationError(str(exc)) from exc
        return ValidatedRule(name=name, params=merged)

    def validate_pipeline(self, rules: Iterable[Mapping[str, Any]]):
        validated = []
        for item in rules:
            validated.append(self.validate_rule(item.get("rule", ""), item.get("params", {})))
        if sum(step.name == SPECIAL_RULE_NAME for step in validated) > 1:
            raise RuleValidationError("Chỉ dùng một luật số ký tự đặc biệt; dùng nút + để chọn nhiều số lượng trong cùng luật.")
        return validated

    def generate(self, rules, profile, min_length: int, max_length: int) -> list[str]:
        if (type(min_length) is not int or type(max_length) is not int
                or min_length < 1 or max_length < min_length):
            raise RuleValidationError("Bộ lọc độ dài phải thỏa mãn 1 ≤ Từ ≤ Đến.")

        steps = self.validate_pipeline(rules)
        special = next((step for step in steps if step.name == SPECIAL_RULE_NAME), None)
        steps = [step for step in steps if step.name != SPECIAL_RULE_NAME]
        # A count-only pipeline still has a source: the legacy mechanical core.
        if not steps:
            steps = [self.validate_rule("LÕI_CƠ_HỌC")]

        # Short bases can become long enough only after symbols are inserted.
        # Apply the final user bounds after the transformation.
        source_min_length = 1 if special else min_length

        passwords = set()
        for step in steps:
            if step.name == "LÕI_CƠ_HỌC":
                passwords.update(handle.generate_basic_wordlist(profile, source_min_length, max_length))
            elif step.name == RULE_NAME:
                passwords.update(RandomNumberRule(**step.params).generate(profile, source_min_length, max_length))
            else:
                raise RuleValidationError(f"Rule chưa được nối vào bộ sinh: {step.name}")
        if special:
            passwords = SpecialCountRule(**special.params).apply(passwords, min_length, max_length)
        return sorted(pw for pw in passwords if min_length <= len(pw) <= max_length)
