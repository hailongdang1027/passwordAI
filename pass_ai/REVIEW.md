# pass_ai review - 2026-09-21

## Da lam
- Xac nhan 4 file tai rieng deu `py_compile` thanh cong.
- Phat hien `main.py` khong chay doc lap vi import `pipeline.logger` trong khi module nay khong co trong bo 4 file; import nay khong duoc su dung trong `main.py` hien tai.
- Tao ban `main.py` de import/test duoc ma khong khoi tao Tkinter ngay khi import: GUI duoc dua vao `build_gui()` va chi chay khi goi file truc tiep.
- Tao `test_safe_helpers.py`; 5/5 test pass.

## Cau truc xac dinh duoc tu RAR
Archive co cac thanh phan chinh:
- `pass_ai/rules/`: `base_rule.py`, `executor.py`, `registry.py`, `rule_pipeline.py`, `name_rule.py`, `date_rule.py`, `leet_rule.py`, `separator_rule.py`, `special_rule.py`, `ai_rule.py`.
- `pass_ai/pipeline/logger.py`.
- `pass_ai/tests/test_pipeline.py`, `pass_ai/tests/test_rule.py`.
- Nhanh code cu `sinhmkcode-main2/` va `rules.cfg` dang nam o nhanh nay.

## Cac loi kien truc da xac dinh tu lan ra soat truoc
- Kien truc can chot ve `rules/ + RuleExecutor` lam luong chinh.
- `separator_rule.py` / `special_rule.py` tham chieu cac ham chua co trong `handle.py`: `generate_direct_separator_patterns`, `generate_separator_joined_variants`, `insert_special_infill`, `get_allowed_positions`.
- `tests/test_rule.py` co dong import bi dinh lien gay SyntaxError: `from rules.leet_rule import LeetRule from rules.executor import RuleExecutor`.
- `rules.cfg` dang o `sinhmkcode-main2/`, khong cung nhanh voi `pass_ai`.

## Ghi chu ve 4 file tai rieng
- `handle.py`: co khoi lap lai `apply_common_patterns(base_str)` va `forced.update(...)` trong `process_and_add()`.
- `main.py`: GUI hien liet ke nhieu Rule nhung nhanh xu ly hien tai chi co logic cho `LOI_CO_HOC`, `TU_HOC_KHUON_MAU`; `LEET` dang `pass`, cac Rule con lai chua duoc noi vao executor.
- `feature_extractor.py` va `ml_ranker.py` deu tu dinh nghia `calculate_entropy()`; nen gom thanh mot utility chung de tranh lech logic.
- Validator GUI chap nhan ngay khuyet `dd/mm` va `mm/yyyy`, nhung `handle.generate_date_variants()` chi xu ly chuoi 8 chu so; hai lop dang khong dong nhat.

## Gioi han cua ban nay
RAR co the doc duoc danh sach file, nhung moi truong hien tai khong co backend `unrar/7z` de giai nen noi dung cac file trong `rules/`. Vi vay ban nay chi sua va test tren 4 file Python duoc tai rieng, khong tu suy doan noi dung cac rule trong archive.
