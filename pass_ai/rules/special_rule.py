# rules/special_rule.py
from .base_rule import BaseRule
from handle import insert_special_infill, get_allowed_positions

class SpecialRule(BaseRule):
    def __init__(self, min_special=1, max_special=1, **kwargs):
        # Lấy số lượng ký tự đặc biệt muốn chèn từ cấu hình UI
        self.min_special = min_special
        self.max_special = max_special

    def execute(self, passwords, profile):
        """
        Duyệt qua các mật khẩu và chèn ký tự đặc biệt vào các vị trí hợp lý.
        """
        new_passwords = set(passwords)

        for pw in passwords:
            # Lấy danh sách các vị trí an toàn để chèn ký tự (dựa trên độ dài từ)
            allowed_pos = get_allowed_positions(pw)
            
            # Gọi hàm chèn ký tự đặc biệt từ file handle.py
            variants = insert_special_infill(
                pw,
                min_special=self.min_special,
                max_special=self.max_special,
                allowed_positions=allowed_pos
            )
            
            new_passwords.update(variants)
            
        return new_passwords