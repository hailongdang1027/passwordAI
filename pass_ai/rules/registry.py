from .base_rule import RuleDefinition
from .random_number_rule import DEFAULT_PARAMS, RULE_NAME
from .special_count_rule import DEFAULT_PARAMS as SPECIAL_DEFAULTS, RULE_NAME as SPECIAL_RULE_NAME


RULE_REGISTRY = {
    SPECIAL_RULE_NAME: RuleDefinition(
        name=SPECIAL_RULE_NAME,
        description="Sinh đúng số ký tự đặc biệt đã chọn (có thể thêm nhiều nhóm bằng +). Áp dụng cuối pipeline; có thêm giới hạn số mẫu mỗi nhóm/chuỗi nền.",
        implemented=True,
        parameter_defaults=SPECIAL_DEFAULTS,
    ),
    "LÕI_CƠ_HỌC": RuleDefinition(
        name="LÕI_CƠ_HỌC",
        description="Luồng xử lý kế thừa hiện có.",
        implemented=True,
    ),
    RULE_NAME: RuleDefinition(
        name=RULE_NAME,
        description="Ghép số ngẫu nhiên với tên, quê quán và nơi làm việc. Chỉ chạy khi được thêm vào danh sách rule.",
        implemented=True,
        parameter_defaults=DEFAULT_PARAMS,
    ),
    "TỰ_HỌC_KHUÔN_MẪU": RuleDefinition(
        name="TỰ_HỌC_KHUÔN_MẪU",
        description="Đã tách khỏi generator; dùng PatternFrequencyModel để phân tích thống kê trước khi tích hợp an toàn.",
        implemented=False,
    ),
    "CAMEL_CASE": RuleDefinition(
        name="CAMEL_CASE",
        description="Chưa được nối vào executor trong bản hiện tại.",
        implemented=False,
    ),
    "LEET": RuleDefinition(
        name="LEET",
        description="Nhánh GUI cũ chỉ có placeholder; chưa triển khai trong executor.",
        implemented=False,
    ),
    "DATE_MIRROR": RuleDefinition(
        name="DATE_MIRROR",
        description="Chưa được nối vào executor trong bản hiện tại.",
        implemented=False,
    ),
    "COUPLE_DATES": RuleDefinition(
        name="COUPLE_DATES",
        description="Chưa được nối vào executor trong bản hiện tại.",
        implemented=False,
    ),
    "COMPANY_HOMETOWN": RuleDefinition(
        name="COMPANY_HOMETOWN",
        description="Chưa được nối vào executor trong bản hiện tại.",
        implemented=False,
    ),
}


def get_available_rule_names(include_unimplemented: bool = False):
    if include_unimplemented:
        return list(RULE_REGISTRY)
    return [name for name, definition in RULE_REGISTRY.items() if definition.implemented]
