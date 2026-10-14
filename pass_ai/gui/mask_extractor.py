import collections

def get_mask(password):
    """Phân rã mật khẩu thành cấu trúc Mask toán học."""
    mask = ""
    for char in password:
        if char.islower():
            mask += "?l" # Chữ thường
        elif char.isupper():
            mask += "?u" # Chữ hoa
        elif char.isdigit():
            mask += "?d" # Số
        else:
            mask += "?s" # Ký tự đặc biệt (khoảng trắng, @, !,...)
    return mask

def analyze_leak_file(file_path, top_n=10):
    """Đọc file rò rỉ và thống kê Top các Khuôn mẫu phổ biến nhất."""
    mask_counter = collections.Counter()
    total_passwords = 0
    
    try:
        # Dùng errors='ignore' để không bị văng lỗi nếu file txt chứa ký tự lạ
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                pwd = line.strip()
                if pwd:
                    mask = get_mask(pwd)
                    mask_counter[mask] += 1
                    total_passwords += 1
                    
        print(f"[*] Đã phân tích tổng cộng: {total_passwords:,} mật khẩu.")
        print(f"[*] TOP {top_n} KHUÔN MẪU (MASK) PHỔ BIẾN NHẤT:")
        print("-" * 50)
        
        for mask, count in mask_counter.most_common(top_n):
            percentage = (count / total_passwords) * 100
            print(f"Mask: {mask:<25} | Số lượng: {count:<8,} | Tỷ lệ: {percentage:.2f}%")
            
    except FileNotFoundError:
        print(f"[!] Không tìm thấy file: {file_path}")

if __name__ == "__main__":
    # Thay tên file bằng file list wifi của bạn
    dataset_file = "wifi_vietnam.txt" 
    analyze_leak_file(dataset_file, top_n=10)