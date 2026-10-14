# pass_ai v3 — CHANGELOG

## AI đọc lõi cơ học — 2026-10-07

- Thêm `core_ai.py` để đọc AST của `handle.py` và nhận diện 9 nhóm chiến lược sinh mật khẩu.
- Thêm `CoreAIRanker`: xếp hạng các kết quả lõi đã sinh theo độ phủ chiến lược và tần suất pattern tổng hợp.
- Thêm giải thích cho từng kết quả: điểm, pattern probability và các chiến lược được nhận diện.
- GUI có nút **Đọc lại handle.py** và tùy chọn **Ưu tiên theo AI khi xuất**; mặc định tắt để giữ nguyên hành vi cũ.
- Thêm `analyze_core.py` để tạo báo cáo màn hình hoặc JSON, không lưu chuỗi hồ sơ/mật khẩu.
- Khi `handle.py` thay đổi, phân tích có thể reload và hiển thị SHA-256 mới.
- Thêm test cho AST, nhận diện chiến lược, ranking, dữ liệu tổng hợp, tính quyết định và callback GUI.

## Bổ sung rule ghép số ngẫu nhiên — 2026-10-05

- Thêm rule `GHÉP_SỐ_NGẪU_NHIÊN`, chỉ thực thi khi người dùng thêm vào danh sách.
- Giao diện có cấu hình số chữ số, số mẫu và vị trí ghép trước/sau/cả hai.
- Ghép số vào biến thể tên, quê quán và công ty; chuẩn hóa tiếng Việt và bỏ qua trường trống.
- Dùng nguồn ngẫu nhiên hệ điều hành, giữ số 0 đầu và giới hạn số mẫu khi không gian số nhỏ.
- Đưa việc điều phối các rule sang `RuleExecutor.generate()`; giữ nguyên nội dung `handle.py`.
- Gộp kết quả với lõi, loại trùng và áp dụng bộ lọc độ dài; giữ hành vi chạy lõi khi danh sách trống.
- Kiểm tra tham số khi thêm và khi chạy; thêm thanh cuộn ngang cho danh sách rule.
- Thêm 17 test, tổng 35 test chạy thành công. Chưa kiểm tra cửa sổ Tkinter thực tế trong môi trường không có màn hình.

## Bổ sung trong v3

- Thêm `PatternFrequencyModel` để học **tần suất cấu trúc tổng hợp** thay vì lưu chuỗi mẫu thô.
- Pattern biểu diễn theo block như `CAP3+SEP_UNDERSCORE+YEAR4`, `LOWER5+DIGIT3`.
- Thêm thống kê độ dài: trung bình, min/max và phân bố theo length.
- GUI có `Top-N`, `Min count`, coverage và vùng preview pattern.
- Thêm xuất báo cáo tổng hợp JSON.
- Thêm xuất bảng pattern CSV UTF-8 BOM để mở thuận tiện bằng Excel.
- CLI `analyze_patterns.py` hỗ trợ đồng thời `--json` và `--csv`.
- Logger chỉ ghi metadata của quá trình phân tích/xuất báo cáo.
- Di chuyển nút chạy pipeline kế thừa vào khung bộ lọc để không bị khuất khi Pattern Lab mở rộng chiều cao GUI.
- Mở rộng bộ test từ 15 lên 18 test; toàn bộ PASS.
- Smoke-test GUI thật bằng Xvfb thành công.

## Giữ nguyên nguyên tắc kiến trúc

- `RuleExecutor` chỉ cho phép rule đã triển khai.
- Các placeholder (`LEET`, `DATE_MIRROR`, `TỰ_HỌC_KHUÔN_MẪU`, ...) không được chạy kiểu no-op.
- Pattern thống kê không được nối trực tiếp vào generator hồ sơ cá nhân.
- `feature_extractor.py` và `ml_ranker.py` vẫn là helper độc lập; chưa có mô hình ML huấn luyện hoàn chỉnh.

## v4 – 2026-10-09

- Thay heuristic scoring bằng logistic regression được train trên dữ liệu có nhãn độc lập.
- Thêm train/validation/test, chia tập theo nhóm nếu có `group_id`, chọn ngưỡng trên validation và chỉ số test held-out.
- Thêm giải thích per-feature theo đóng góp log-odds, format JSON an toàn không lưu chuỗi mật khẩu.
- Loại bỏ trọng số xếp hạng danh sách dự đoán và tùy chọn ưu tiên theo AI.
- Thêm GUI cửa sổ riêng, CLI, bộ dữ liệu mô phỏng, mô hình demo, test ML.
