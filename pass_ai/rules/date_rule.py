# rules/date_rule.py
from .base_rule import BaseRule
from handle import generate_date_variants

class DateRule(BaseRule):
    def __init__(self, format="YEAR", **kwargs):
        self.format = format

    def execute(self, passwords, profile):
        """
        Sinh biến thể ngày tháng và ghép vào các mật khẩu hiện có.
        """
        date_fields = ["birthdate", "relative_birth", "child_birth"]
        new_passwords = set(passwords) # Tạo bản sao để tránh lỗi thay đổi set khi lặp

        for field in date_fields:
            if profile.get(field):
                # Gọi hàm sinh ngày từ handle.py
                date_vars = generate_date_variants(profile[field])
                
                # Nếu chưa có Base Password nào, tự thêm ngày tháng làm Base
                if not passwords:
                    new_passwords.update(date_vars)
                else:
                    # Ghép ngày tháng vào đuôi các mật khẩu đang có
                    for pw in passwords:
                        for dv in date_vars:
                            new_passwords.add(pw + dv)
                            
        return new_passwords