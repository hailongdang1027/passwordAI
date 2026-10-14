# Hướng dẫn cập nhật AI v4 – Huấn luyện / Kiểm định / Giải thích

Phiên bản này cập nhật **toàn bộ thư mục `pass_ai`** trên cơ sở gói RAR bạn cung cấp. Các tệp trong `sinhmkcode-main2` được giữ nguyên.

## Cài đặt nhanh trên Windows

1. Giải nén `sinhmatkhauAI_AI_v4.zip`.
2. Mở terminal tại `sinhmatkhauAI/pass_ai`.
3. Chạy `py -m pip install -r requirements.txt`.
4. Chạy `py main.py`.
5. Bấm **Mở cửa sổ ML: Huấn luyện / Kiểm định / Giải thích**.
6. Bấm **Huấn luyện từ CSV**, chọn `examples/demo_labeled_synthetic.csv` để thử toàn bộ quy trình. Sau khi chạy, xem `models/password_strength.json` và `output/password_strength_metrics.json`.
7. Muốn thử ngay phần dự đoán mà không huấn luyện, bấm **Nạp mô hình**, chọn `examples/demo_model.json`, sau đó nhập một mật khẩu thử nghiệm vào ô ẩn và bấm **Đánh giá riêng lẻ**.

> Dữ liệu/mô hình `demo_*` chỉ dùng minh họa kỹ thuật; không đánh giá chính xác độ an toàn mật khẩu trong thực tế. Muốn làm nghiên cứu hoặc triển khai phải có bộ dữ liệu được phép, có nhãn chất lượng và chia nhóm đúng cách.

## Lệnh cơ bản

```powershell
py train_model.py train --data examples/demo_labeled_synthetic.csv
py train_model.py explain --model models/password_strength.json
py -m unittest -v test_safe_helpers.py test_random_number_rule.py test_core_ai.py test_ml_model.py
```

## Điểm thay đổi chính

- Xóa hàm chấm điểm heuristic trong `ml_ranker.py`.
- Xóa công thức trộn điểm và tùy chọn ưu tiên mật khẩu dự đoán theo AI; mô hình mới **không liên kết với bộ sinh theo hồ sơ cá nhân**.
- Xóa hàm nhân trọng số chấm điểm không còn dùng trong `handle.py`.
- Thêm mô hình Logistic Regression học từ CSV `password,label`, có thể có `group_id`; có train / validation / test, confusion matrix, Balanced Accuracy, F1, ROC-AUC, Brier.
- Mô hình JSON và báo cáo JSON chỉ chứa thông số và thống kê, không chứa mật khẩu thô.
- Giải thích trên mỗi mật khẩu bằng đóng góp vào log-odds dự đoán, không dùng công thức điểm thưởng/phạt tùy ý.

Chi tiết và hạn chế nghiên cứu xem `pass_ai/README.md`.
