# pass_ai v4 – Mô hình học máy đánh giá độ mạnh mật khẩu

Bản cập nhật v4 được xây dựng từ dự án `sinhmatkhauAI(3).rar`. Phần đánh giá mật khẩu không còn các công thức cộng/trừ điểm do người viết chương trình ấn định. Thay vào đó là **Logistic Regression được huấn luyện bằng dữ liệu có nhãn**, đánh giá trên dữ liệu độc lập và giải thích được từng dự đoán.

> **Phạm vi:** AI mới dùng để **đánh giá riêng lẻ một mật khẩu** theo nhãn độ mạnh đã cho. AI không xếp hạng mật khẩu dự đoán dựa trên tên, ngày sinh, người thân hay danh sách từ điển. Các chức năng tạo mẫu/từ điển của dự án gốc vẫn được giữ như chức năng độc lập, không được kết nối với mô hình mới.

## 1. Cài đặt trên Windows

Yêu cầu **Python 3.10+** có Tkinter. Từ thư mục `sinhmatkhauAI/pass_ai`:

```powershell
py -m pip install -r requirements.txt
py main.py
```

Nếu không có lệnh `py`, thử `python` thay thế. Chương trình hoạt động tại máy, không cần Docker/API hoặc kết nối máy chủ.

Trong giao diện chính, bấm **Mở cửa sổ ML: Huấn luyện / Kiểm định / Giải thích**. Cửa sổ ML độc lập cho phép:

1. **Huấn luyện từ CSV:** chọn file CSV đã gán nhãn; kết quả gồm mô hình `models/password_strength.json` và báo cáo `output/password_strength_metrics.json`.
2. **Nạp mô hình:** mở file JSON tham số của mô hình, ví dụ `examples/demo_model.json` để thử giao diện.
3. **Đánh giá riêng lẻ:** nhập một mật khẩu trong ô được che ký tự, nhấn nút đánh giá. Ô nhập được xóa ngay khi nhấn; kết quả hiển thị nhãn dự đoán, xác suất nhãn mạnh và các đóng góp đặc trưng (không hiển thị lại chuỗi).

Các phần Pattern Lab và chức năng gốc được giữ nguyên, ngoại trừ tùy chọn cũ **“Ưu tiên theo AI khi xuất”** đã được loại bỏ. Công cụ đọc AST `handle.py` vẫn dùng để mô tả các cơ chế của mã nguồn, không dùng để chấm điểm mật khẩu.

## 2. Dữ liệu huấn luyện

CSV bắt buộc có `password,label`. Có thể thêm `group_id` để gom các mẫu liên quan (cùng nguồn/cùng gia đình biến thể) vào một nhóm, tránh rò rỉ thông tin giữa các tập.

```csv
password,label,group_id
sample,0,weak-family-a
example123,0,weak-family-b
Longer_Phrase!With123Chars,1,strong-family-a
Another#Long_Phrase9876,1,strong-family-b
```

* Nhãn `0` nghĩa là **yếu**, nhãn `1` nghĩa là **mạnh**, theo phương pháp gán nhãn của chủ sở hữu dữ liệu. **Không tự gán nhãn bằng chính các công thức chấm điểm cũ**, nếu không mô hình chỉ học lại quy tắc thủ công.
* Cần ít nhất **60 mật khẩu riêng biệt**, trong đó mỗi lớp có ít nhất **20 mẫu**. Khuyến nghị tập lớn hơn nhiều, được thu thập hợp pháp, có tiêu chuẩn gán nhãn độc lập và nhất quán.
* Không dùng trực tiếp `gui/wifi_vietnam.txt` để huấn luyện phân loại: đó là file chỉ có chuỗi, **không có nhãn 0/1**.
* Dòng trùng mật khẩu được loại bỏ trước khi chia tập; nhãn hoặc nhóm mâu thuẫn bị từ chối. Nếu dùng `group_id`, cần ít nhất 15 nhóm và các nhóm phải phân bổ đủ cả hai nhãn trong ba tập.
* **Không nhập mật khẩu thật đang sử dụng** vào file dữ liệu minh họa; CSV là văn bản thuần, nên dùng dữ liệu mô phỏng hoặc dữ liệu kiểm thử được phép.

Dữ liệu minh họa 144 dòng: `examples/demo_labeled_synthetic.csv`. Các nhãn là nhãn **tổng hợp để kiểm thử kỹ thuật**; không phải cơ sở khoa học để khẳng định mật khẩu an toàn.

## 3. Huấn luyện từ dòng lệnh

```powershell
cd sinhmatkhauAI\pass_ai
py -m pip install -r requirements.txt
py train_model.py train --data examples/demo_labeled_synthetic.csv
```

Mặc định các tệp đầu ra là:

* `models/password_strength.json`: phiên bản bộ đặc trưng, trung bình, độ lệch chuẩn, hệ số, hệ số chệch, ngưỡng được chọn trên tập validation và metadata. **Không chứa mẫu mật khẩu thô.**
* `output/password_strength_metrics.json`: quy mô các tập, ma trận nhầm lẫn, accuracy, balanced accuracy, precision, recall, F1, ROC-AUC, Brier score, hệ số đặc trưng. **Không chứa mật khẩu thô.**

Có thể tùy chỉnh:

```powershell
py train_model.py train --data du_lieu_co_nhan.csv --model models/moi.json --report output/bao_cao.json --seed 42
```

Để kiểm tra **một mật khẩu riêng lẻ** qua terminal mà không đưa nó vào lịch sử lệnh:

```powershell
py train_model.py explain --model models/password_strength.json
```

Chương trình dùng `getpass()` để nhận mật khẩu ẩn. Không sử dụng cách truyền mật khẩu trên tham số CLI.

## 4. Huấn luyện, kiểm định và giải thích

Luồng kỹ thuật:

```text
CSV được gán nhãn và được phép
    → xác thực nhãn + loại mẫu trùng
    → đo 11 đặc trưng hình thái (KHÔNG cộng điểm thủ công)
    → chia Train / Validation / Test ~60% / 20% / 20%
         (có group_id: chia theo nhóm không giao nhau)
    → StandardScaler + LogisticRegression học trọng số bằng Train
    → chọn ngưỡng Balanced Accuracy chỉ trên Validation
    → đánh giá đúng một lần trên Test chưa thấy
    → lưu JSON mô hình + JSON metrics
    → nhập một mật khẩu → suy luận → giải thích đóng góp đặc trưng
```

Các đặc trưng là phép đo: độ dài, tỷ lệ chữ thường/chữ hoa/chữ số/ký tự khác, tỷ lệ ký tự khác nhau, độ dài chuỗi lặp, chuỗi số, chuỗi chữ, entropy Shannon và số lớp ký tự. **Không đặc trưng nào tự có điểm thưởng/phạt**; trọng số được mô hình học từ nhãn.

**Giải thích cục bộ:** Với hồi quy logistic chuẩn hóa, tổng `intercept + Σ(coefficient × (feature − mean) / scale)` là log-odds dự đoán lớp `strong`. Phần giải thích hiển thị dấu `+` hoặc `−` của từng đóng góp. Các hệ số tiêu chuẩn hóa cũng được lưu trong báo cáo để tham khảo toàn cục.

**Ý nghĩa kết quả:** `P(nhãn mạnh)` là **xác suất mô hình dự đoán nhãn “mạnh” theo dữ liệu huấn luyện**, không phải xác suất mật khẩu không thể bị dò hoặc xác suất bị lộ. Báo cáo minh họa có thể có kết quả hoàn hảo bởi vì tập dữ liệu nhân tạo và dễ phân biệt; **không được trích dẫn như kết quả kiểm định thực địa**. Cần kiểm chứng bằng bộ dữ liệu độc lập, nguồn và phương pháp gán nhãn rõ ràng, và xem xét hiệu chỉnh xác suất trước khi triển khai thực tế.

## 5. Thay đổi so với phiên bản v3

| Hạng mục | v3 | v4 |
|---|---|---|
| `ml_ranker.py` | Cộng điểm heuristics | Mô hình LogisticRegression được huấn luyện từ nhãn |
| `core_ai.py` | Trộn 65% pattern + 35% strategy để xếp hạng | Chỉ phân tích AST lõi (không xếp hạng) |
| `feature_extractor.py` | 12 phép đo gồm mẫu đặc thù | 11 phép đo hình thái tổng quát, phiên bản hóa |
| `handle.py` | Còn hàm trọng số thủ công không dùng | Loại bỏ hàm trọng số, giữ tập ký tự đặc biệt |
| `main.py` | Có tùy chọn ưu tiên danh sách theo AI | Có cửa sổ riêng train/validate/explain một mật khẩu |
| `train_model.py` | Chưa có | CLI huấn luyện/suy luận và báo cáo |
| Kiểm thử | Không có đánh giá ML thực sự | Có tách tập, ma trận nhầm lẫn, ROC-AUC, Brier, test lưu/nạp |

## 6. Chạy kiểm thử

```powershell
py -m unittest -v test_safe_helpers.py test_random_number_rule.py test_core_ai.py test_ml_model.py
```

Script cũ `tests/test_rule.py` vốn có lỗi cú pháp `from ... import ... from ...` trong dự án đầu vào; không thuộc bộ test được duy trì. GUI đã được kiểm tra ở mức callback mô phỏng, **chưa kiểm tra trực quan Tkinter trên Windows** trong môi trường chạy không có màn hình.

### Cấu trúc quan trọng

```text
pass_ai/
  main.py                 # Tkinter + cửa sổ ML
  ml_ranker.py            # Train/Validate/Test, lưu mô hình, giải thích
  feature_extractor.py    # 11 phép đo không trọng số
  train_model.py          # CLI
  core_ai.py              # Đọc AST, KHÔNG xếp hạng mật khẩu
  examples/
    demo_labeled_synthetic.csv
    demo_model.json       # MÔ HÌNH MINH HỌA, KHÔNG DÙNG THỰC TẾ
    demo_evaluation.json  # CHỈ KIỂM THỬ KỸ THUẬT
  test_ml_model.py
  requirements.txt
```
