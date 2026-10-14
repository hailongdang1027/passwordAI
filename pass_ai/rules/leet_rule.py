# rules/leet_rule.py
from .base_rule import BaseRule
from handle import generate_leet_variants

class LeetRule(BaseRule):
    def __init__(self, max_change=2, **kwargs):
        # Lấy tham số max_change từ cấu hình của người dùng (mặc định là 2)
        self.max_change = max_change

    def execute(self, passwords, profile):
        """
        Duyệt qua các mật khẩu hiện tại, tạo các biến thể Leetspeak (ví dụ: a -> @, e -> 3)
        và bổ sung vào tập kết quả.
        """
        new_passwords = set(passwords) # Copy để không báo lỗi khi thay đổi set trong lúc lặp

        for pw in passwords:
            # Gọi hàm sinh biến thể leet từ file handle.py
            # Đặt min_changes=1 để đảm bảo có sự thay đổi thực sự
            variants = generate_leet_variants(pw, min_changes=1, max_changes=self.max_change)
            new_passwords.update(variants)
            
        return new_passwords