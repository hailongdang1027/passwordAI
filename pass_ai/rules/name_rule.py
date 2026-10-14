# rules/name_rule.py
from .base_rule import BaseRule
from handle import parse_vietnamese_name

class NameRule(BaseRule):
    def __init__(self, **kwargs):
        pass

    def execute(self, passwords, profile):
        """
        Lấy tên từ profile, phân tích thành các biến thể và thêm vào set passwords.
        """
        for field in ["fullname", "relative_name", "child_name"]:
            if not profile.get(field):
                continue
            
            # Gọi hàm xử lý từ handle.py
            info = parse_vietnamese_name(profile[field])
            if info and "variants" in info:
                passwords.update(info["variants"])
                
        return passwords