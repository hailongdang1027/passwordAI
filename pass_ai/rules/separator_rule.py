# rules/separator_rule.py
from .base_rule import BaseRule
from handle import (
    generate_direct_separator_patterns, 
    parse_vietnamese_name, 
    generate_separator_joined_variants
)

class SeparatorRule(BaseRule):
    def __init__(self, max_separators=3, chars="_,-", **kwargs):
        # Thiết lập số lượng và loại ký tự phân cách (mặc định lấy _, -)
        self.max_separators = int(max_separators)
        self.separator_chars = [c.strip() for c in chars.split(",")]

    def execute(self, passwords, profile):
        """
        Sinh các biến thể mật khẩu có chứa dấu phân cách giữa các token thông tin.
        """
        new_passwords = set(passwords)

        # 1. Nối trực tiếp các trường thông tin (Tên + Ngày sinh người thân, v.v.)
        # Hàm này đã duyệt sẵn tổ hợp các trường trong profile từ handle.py
        direct_patterns = generate_direct_separator_patterns(profile)
        new_passwords.update(direct_patterns)

        # 2. Xử lý chuyên sâu cho các thành phần Tên (Họ_Tên_Đệm)
        for field in ["fullname", "relative_name", "child_name"]:
            if not profile.get(field):
                continue
                
            info = parse_vietnamese_name(profile[field])
            if info:
                # Trích xuất các mảnh của tên để trộn
                parts = []
                if info.get("surname"): 
                    parts.append(info["surname"])
                if info.get("middle"): 
                    parts.extend(info["middle"])
                if info.get("given"): 
                    parts.append(info["given"])
                
                # Gọi hàm sinh biến thể nối từ handle.py nếu có >= 2 thành phần
                if len(parts) >= 2:
                    variants = generate_separator_joined_variants(
                        parts,
                        separator_chars=self.separator_chars,
                        max_separators=self.max_separators
                    )
                    new_passwords.update(variants)
                    
        return new_passwords