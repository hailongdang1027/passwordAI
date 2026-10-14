from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class RuleDefinition:
    name: str
    description: str
    implemented: bool = False
    parameter_defaults: Mapping[str, Any] = field(default_factory=dict)
