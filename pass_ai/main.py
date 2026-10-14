#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import re
import json
from collections import Counter
from datetime import datetime

import handle
from pipeline.logger import PipelineLogger
from rules import RULE_REGISTRY, RuleExecutor, RuleValidationError, get_available_rule_names
from rules.random_number_rule import DEFAULT_PARAMS as RANDOM_DEFAULTS, RULE_NAME as RANDOM_RULE_NAME
from rules.special_count_rule import DEFAULT_PARAMS as SPECIAL_DEFAULTS, RULE_NAME as SPECIAL_RULE_NAME, count_specials
from pattern_model import PatternFrequencyModel
from core_ai import analyze_core_source, format_core_analysis
from ml_ranker import PasswordStrengthModel, train_model
from pathlib import Path

handle.read_config("rules.cfg")
rule_executor = RuleExecutor()
pipeline_logger = PipelineLogger()

DEFAULT_ENTRY_BG = "white"
ERROR_ENTRY_BG = "#ffd6d6"
RANDOM_POSITIONS = {"Cả trước và sau": "both", "Trước": "prefix", "Sau": "suffix"}
SPECIAL_POSITIONS = {"Ưu tiên đầu/cuối": "prefer_edges", "Bất kỳ vị trí": "any", "Chỉ đầu/cuối": "edges"}
special_count_rows = []
frame_special_params = None

active_rules = []
pattern_model = PatternFrequencyModel()
core_analysis = None
strength_model = None
APP_DIR = Path(__file__).resolve().parent
DEFAULT_STRENGTH_MODEL = APP_DIR / "models" / "password_strength.json"
DEFAULT_STRENGTH_REPORT = APP_DIR / "output" / "password_strength_metrics.json"

# ==========================================
# PHÂN TÍCH KHUÔN MẪU THỐNG KÊ
# ==========================================
def get_mask(password):
    """Legacy helper kept for compatibility with older tests/tools."""
    mask = ""
    for char in password:
        if char.islower(): mask += "?l"
        elif char.isupper(): mask += "?u"
        elif char.isdigit(): mask += "?d"
        else: mask += "?s"
    return mask

def build_pattern_preview(model, limit=10, min_count=1):
    """Return a text-only aggregate preview; never includes raw samples."""
    rows = model.top_patterns(limit=max(int(limit), 1), min_count=max(int(min_count), 1))
    if not rows:
        return "(Không có pattern phù hợp bộ lọc)"
    lines = [f"{'Tỷ lệ':>8}  {'Số mẫu':>7}  Pattern"]
    lines.append("-" * 58)
    for row in rows:
        lines.append(f"{row.probability:>7.2%}  {row.count:>7d}  {row.pattern}")
    return "\n".join(lines)


def _pattern_view_options():
    try:
        limit = max(int(entry_pattern_top.get().strip() or "10"), 1)
        min_count = max(int(entry_pattern_min_count.get().strip() or "1"), 1)
    except ValueError as exc:
        raise ValueError("Top-N và Min count phải là số nguyên dương.") from exc
    return limit, min_count


def refresh_pattern_preview(show_errors=True):
    if pattern_model.total_samples <= 0:
        if show_errors:
            messagebox.showwarning("Chưa có dữ liệu", "Hãy nạp dataset được phép trước.")
        return
    try:
        limit, min_count = _pattern_view_options()
    except ValueError as exc:
        if show_errors:
            messagebox.showerror("Bộ lọc không hợp lệ", str(exc))
        return

    coverage = pattern_model.coverage(limit=limit, min_count=min_count)
    preview = build_pattern_preview(pattern_model, limit=limit, min_count=min_count)
    txt_pattern_preview.config(state=tk.NORMAL)
    txt_pattern_preview.delete('1.0', tk.END)
    txt_pattern_preview.insert(tk.END, preview)
    txt_pattern_preview.config(state=tk.DISABLED)

    lbl_pattern_metrics.config(
        text=(
            f"Mẫu: {pattern_model.total_samples} | Pattern: {len(pattern_model.pattern_counts)} | "
            f"Độ dài TB: {pattern_model.average_length:.2f} | Khoảng: "
            f"{pattern_model.min_length}-{pattern_model.max_length} | Coverage: {coverage:.1%}"
        )
    )


def show_core_ai_analysis():
    """Read the mechanical core statically and show its detected strategies."""
    global core_analysis
    try:
        core_analysis = analyze_core_source(APP_DIR / "handle.py")
        analysis_text = format_core_analysis(core_analysis)
        txt_core_analysis.config(state=tk.NORMAL)
        txt_core_analysis.delete("1.0", tk.END)
        txt_core_analysis.insert(tk.END, analysis_text)
        txt_core_analysis.config(state=tk.DISABLED)
        lbl_core_ai_status.config(
            text=(
                f"Đã đọc {len(core_analysis.functions)} hàm, "
                f"nhận diện {len(core_analysis.strategies)} chiến lược"
            ),
            fg="green",
        )
        pipeline_logger.log(
            "core_ai_analyzed",
            function_count=len(core_analysis.functions),
            strategy_count=len(core_analysis.strategies),
            source_sha256=core_analysis.source_sha256,
        )
    except Exception as exc:
        messagebox.showerror("Lỗi đọc lõi", f"Không thể phân tích handle.py: {exc}")


def load_pattern_dataset():
    """Analyze an authorized/synthetic dataset and keep aggregate patterns only."""
    filepath = filedialog.askopenfilename(
        title="Chọn dataset được phép để phân tích cấu trúc",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
    )
    if not filepath:
        return

    try:
        pattern_model.fit_file(filepath)
        refresh_pattern_preview(show_errors=False)
        limit, min_count = _pattern_view_options()
        coverage = pattern_model.coverage(limit=limit, min_count=min_count)

        lbl_leak_status.config(
            text=f"✅ {os.path.basename(filepath)} — đã phân tích dữ liệu tổng hợp",
            fg="green",
        )
        pipeline_logger.log(
            "pattern_dataset_analyzed",
            sample_count=pattern_model.total_samples,
            unique_pattern_count=len(pattern_model.pattern_counts),
            average_length=round(pattern_model.average_length, 4),
            coverage=round(coverage, 6),
            top_limit=limit,
            min_count=min_count,
        )
        messagebox.showinfo(
            "Phân tích hoàn tất",
            f"Đã phân tích {pattern_model.total_samples} mẫu.\n"
            f"Số pattern duy nhất: {len(pattern_model.pattern_counts)}\n"
            f"Độ dài trung bình: {pattern_model.average_length:.2f}\n"
            f"Coverage theo bộ lọc hiện tại: {coverage:.1%}\n\n"
            "Chỉ số liệu tổng hợp được giữ trong mô hình; chuỗi đầu vào không được lưu lại.",
        )
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể phân tích dataset: {e}")


def export_pattern_json():
    if pattern_model.total_samples <= 0:
        messagebox.showwarning("Chưa có dữ liệu", "Hãy nạp dataset trước khi xuất báo cáo.")
        return
    try:
        limit, min_count = _pattern_view_options()
    except ValueError as exc:
        messagebox.showerror("Bộ lọc không hợp lệ", str(exc))
        return
    path = filedialog.asksaveasfilename(
        title="Xuất báo cáo JSON tổng hợp",
        defaultextension=".json",
        filetypes=[("JSON", "*.json")],
    )
    if not path:
        return
    try:
        pattern_model.export_summary(path, limit=limit, min_count=min_count)
        pipeline_logger.log("pattern_summary_exported", format="json", pattern_limit=limit, min_count=min_count)
        messagebox.showinfo("Đã xuất", f"Đã lưu báo cáo JSON:\n{os.path.abspath(path)}")
    except Exception as exc:
        messagebox.showerror("Lỗi xuất báo cáo", str(exc))


def export_pattern_csv():
    if pattern_model.total_samples <= 0:
        messagebox.showwarning("Chưa có dữ liệu", "Hãy nạp dataset trước khi xuất báo cáo.")
        return
    try:
        limit, min_count = _pattern_view_options()
    except ValueError as exc:
        messagebox.showerror("Bộ lọc không hợp lệ", str(exc))
        return
    path = filedialog.asksaveasfilename(
        title="Xuất bảng pattern CSV",
        defaultextension=".csv",
        filetypes=[("CSV", "*.csv")],
    )
    if not path:
        return
    try:
        pattern_model.export_patterns_csv(path, limit=limit, min_count=min_count)
        pipeline_logger.log("pattern_summary_exported", format="csv", pattern_limit=limit, min_count=min_count)
        messagebox.showinfo("Đã xuất", f"Đã lưu bảng CSV:\n{os.path.abspath(path)}")
    except Exception as exc:
        messagebox.showerror("Lỗi xuất báo cáo", str(exc))

def open_strength_window():
    """Use a separate window so added ML controls do not crowd legacy forms."""
    global entry_strength_password, txt_strength_explanation, lbl_strength_status
    global strength_window
    if "strength_window" in globals() and strength_window.winfo_exists():
        strength_window.lift()
        return
    window = tk.Toplevel(root)
    strength_window = window
    window.title("Mô hình học máy: huấn luyện - kiểm định - giải thích")
    window.geometry("670x380")
    frame_strength = tk.LabelFrame(
        window, text="Học máy: đánh giá độ mạnh 1 mật khẩu (có nhãn)",
        padx=6, pady=6, bg="#f0f8ff",
    )
    frame_strength.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    buttons_strength = tk.Frame(frame_strength, bg="#f0f8ff")
    buttons_strength.pack(fill=tk.X)
    tk.Button(buttons_strength, text="Huấn luyện từ CSV", command=train_strength_model_gui).pack(side=tk.LEFT, padx=(0, 4))
    tk.Button(buttons_strength, text="Nạp mô hình", command=load_strength_model_gui).pack(side=tk.LEFT)
    lbl_strength_status = tk.Label(frame_strength, text="Chưa nạp mô hình đã huấn luyện.", bg="#f0f8ff", fg="#555")
    lbl_strength_status.pack(anchor="w")
    password_row = tk.Frame(frame_strength, bg="#f0f8ff")
    password_row.pack(fill=tk.X, pady=(4, 2))
    tk.Label(password_row, text="Mật khẩu cần kiểm tra:", bg="#f0f8ff").pack(side=tk.LEFT)
    entry_strength_password = tk.Entry(password_row, show="•", width=20)
    entry_strength_password.pack(side=tk.LEFT, padx=5)
    tk.Button(password_row, text="Đánh giá riêng lẻ", command=assess_single_password).pack(side=tk.LEFT)
    txt_strength_explanation = tk.Text(frame_strength, height=6, width=56, font=("Consolas", 8), state=tk.DISABLED)
    txt_strength_explanation.pack(fill=tk.X)
    if DEFAULT_STRENGTH_MODEL.exists():
        try:
            _load_strength_model(DEFAULT_STRENGTH_MODEL)
        except Exception as exc:
            lbl_strength_status.config(text=f"Không thể nạp mô hình mặc định: {exc}", fg="red")


def _load_strength_model(path):
    global strength_model
    strength_model = PasswordStrengthModel.load(path)
    lbl_strength_status.config(
        text=f"Đã nạp: {Path(path).name} | ngưỡng kiểm định {strength_model.threshold:.3f}",
        fg="green",
    )


def load_strength_model_gui():
    path = filedialog.askopenfilename(title="Mở mô hình JSON đã huấn luyện", filetypes=[("JSON", "*.json")])
    if not path:
        return
    try:
        _load_strength_model(path)
    except Exception as exc:
        messagebox.showerror("Không thể nạp mô hình", str(exc))


def train_strength_model_gui():
    path = filedialog.askopenfilename(title="CSV có nhãn password,label", filetypes=[("CSV", "*.csv")])
    if not path:
        return
    try:
        report = train_model(path, DEFAULT_STRENGTH_MODEL, DEFAULT_STRENGTH_REPORT)
        _load_strength_model(DEFAULT_STRENGTH_MODEL)
        test = report["test"]
        messagebox.showinfo(
            "Huấn luyện và kiểm định xong",
            f"Tập kiểm thử độc lập: {test['count']} mẫu\n"
            f"Balanced accuracy: {test['balanced_accuracy']:.3f}\n"
            f"F1 (nhãn mạnh): {test['f1_strong']:.3f}\n"
            f"ROC-AUC: {test['roc_auc']:.3f}\n"
            f"Báo cáo: {DEFAULT_STRENGTH_REPORT}\n\n"
            "Chỉ số phụ thuộc chất lượng nhãn, không phải xác suất mật khẩu bị dò được.",
        )
    except Exception as exc:
        messagebox.showerror("Không thể huấn luyện", str(exc))


def assess_single_password():
    password = entry_strength_password.get()
    entry_strength_password.delete(0, tk.END)
    if strength_model is None:
        messagebox.showwarning("Thiếu mô hình", "Huấn luyện hoặc nạp mô hình trước khi đánh giá.")
        return
    if not password:
        messagebox.showwarning("Thiếu dữ liệu", "Nhập một mật khẩu vào ô nhập ẩn.")
        return
    try:
        result = strength_model.explain(password)
        prediction = "MẠNH" if result["prediction"] == "strong" else "YẾU"
        lines = [
            f"Dự đoán: {prediction} | P(nhãn mạnh)={result['probability_strong']:.1%}",
            "Tác động lên log-odds dự đoán (+ tăng, - giảm xác suất nhãn mạnh):",
        ]
        lines.extend(f"  {row['contribution_log_odds']:+.3f}  {row['label']}"
                     for row in result["contributions"])
        lines.append("Phân loại thống kê theo nhãn tập huấn luyện; KHÔNG bảo đảm an toàn.")
        txt_strength_explanation.config(state=tk.NORMAL)
        txt_strength_explanation.delete("1.0", tk.END)
        txt_strength_explanation.insert(tk.END, "\n".join(lines))
        txt_strength_explanation.config(state=tk.DISABLED)
    except Exception as exc:
        messagebox.showerror("Không thể đánh giá", str(exc))


# ==========================================
# CÁC HÀM KIỂM TRA ĐẦU VÀO (VALIDATORS)
# ==========================================
def validate_name_field(event):
    widget = event.widget
    val = widget.get().strip()
    if not val:
        widget.config(bg=DEFAULT_ENTRY_BG)
        return
    if re.match(r"^[a-zA-ZÀ-ỹ\s]+$", val):
        widget.config(bg=DEFAULT_ENTRY_BG)
    else:
        widget.config(bg=ERROR_ENTRY_BG)

def is_valid_flexible_date(date_str):
    date_str = date_str.strip()
    if not date_str: return True
    now = datetime.now()
    try:
        if len(date_str) == 10 and date_str.count('/') == 2:
            input_date = datetime.strptime(date_str, "%d/%m/%Y")
            if input_date.date() > now.date(): return False
            return True
        elif len(date_str) == 5 and date_str.count('/') == 1:
            parts = date_str.split('/')
            if len(parts[1]) == 2:
                datetime.strptime(date_str + "/2000", "%d/%m/%Y")
                return True
        elif len(date_str) == 7 and date_str.count('/') == 1:
            parts = date_str.split('/')
            if len(parts[1]) == 4:
                input_date = datetime.strptime("01/" + date_str, "%d/%m/%Y")
                current_month = now.replace(day=1)
                if input_date.date() > current_month.date(): return False
                return True
        return False
    except ValueError:
        return False

def make_date_validator(entry_widget):
    def _on_focus_out(event=None):
        if is_valid_flexible_date(entry_widget.get()):
            entry_widget.config(bg=DEFAULT_ENTRY_BG)
        else:
            entry_widget.config(bg=ERROR_ENTRY_BG)
    return _on_focus_out

def clean_date(date_str):
    return date_str.replace("/", "").replace("-", "").strip()

# ==========================================
# CÁC HÀM XỬ LÝ PIPELINE & RULE
# ==========================================
def parse_params(param_str):
    params = {}
    if not param_str.strip(): return params
    pairs = param_str.split(',')
    for pair in pairs:
        if '=' in pair:
            k, v = pair.split('=', 1)
            k, v = k.strip(), v.strip()
            params[k] = int(v) if v.isdigit() else v
    return params

def on_rule_selected(event=None):
    rule_name = combo_rule.get().strip()
    definition = RULE_REGISTRY.get(rule_name)
    lbl_rule_description.config(text=definition.description if definition else "")
    if frame_special_params is not None:
        frame_special_params.grid_remove()
    if rule_name == RANDOM_RULE_NAME:
        frame_random_params.grid()
        entry_params.config(state=tk.DISABLED)
    else:
        frame_random_params.grid_remove()
        if rule_name == SPECIAL_RULE_NAME:
            if frame_special_params is not None:
                frame_special_params.grid()
            entry_params.config(state=tk.DISABLED)
        else:
            entry_params.config(state=tk.NORMAL)


def remove_special_count_row(row, entry):
    if len(special_count_rows) > 1:
        special_count_rows.remove((row, entry))
        row.destroy()


def add_special_count_row(value=None):
    if value is None:
        used = {entry.get().strip() for _, entry in special_count_rows}
        value = next((n for n in list(range(1, 65)) + [0] if str(n) not in used), None)
        if value is None:
            messagebox.showinfo("Số lượng", "Đã có đủ các số lượng từ 0 đến 64.")
            return
    row = tk.Frame(frame_special_counts)
    row.pack(fill=tk.X, pady=1)
    tk.Label(row, text="Đúng").pack(side=tk.LEFT)
    entry = tk.Spinbox(row, from_=0, to=64, width=5)
    entry.delete(0, tk.END)
    entry.insert(0, str(value))
    entry.pack(side=tk.LEFT, padx=4)
    tk.Label(row, text="ký tự đặc biệt").pack(side=tk.LEFT)
    tk.Button(row, text="−", width=2, command=lambda: remove_special_count_row(row, entry)).pack(side=tk.RIGHT)
    special_count_rows.append((row, entry))


def add_rule():
    rule_name = combo_rule.get().strip()
    
    if not rule_name:
        return
    if rule_name == RANDOM_RULE_NAME:
        parsed_params = {
            "min_digits": entry_random_min.get(),
            "max_digits": entry_random_max.get(),
            "count": entry_random_count.get(),
            "position": RANDOM_POSITIONS.get(combo_random_position.get(), ""),
        }
    elif rule_name == SPECIAL_RULE_NAME:
        parsed_params = {
            "counts": [entry.get() for _, entry in special_count_rows],
            "characters": entry_special_characters.get(),
            "position": SPECIAL_POSITIONS.get(combo_special_position.get(), ""),
            "samples": entry_special_samples.get(),
        }
    else:
        parsed_params = parse_params(entry_params.get().strip())
    try:
        validated = rule_executor.validate_rule(rule_name, parsed_params)
    except RuleValidationError as exc:
        messagebox.showerror("Rule không hợp lệ", str(exc))
        return

    display_text = f"[{validated.name}] "
    if validated.params:
        param_texts = [f"{k}={v}" for k, v in validated.params.items()]
        display_text += f"({', '.join(param_texts)})"
    
    existing = next((i for i, item in enumerate(active_rules)
                     if rule_name == SPECIAL_RULE_NAME and item["rule"] == SPECIAL_RULE_NAME), None)
    item = {"rule": validated.name, "params": validated.params}
    if existing is None:
        active_rules.append(item)
        listbox_rules.insert(tk.END, display_text)
    else:
        active_rules[existing] = item
        listbox_rules.delete(existing)
        listbox_rules.insert(existing, display_text)
    pipeline_logger.log("rule_added" if existing is None else "rule_updated",
                        rule=validated.name, parameter_count=len(validated.params))
    if rule_name not in (RANDOM_RULE_NAME, SPECIAL_RULE_NAME):
        entry_params.delete(0, tk.END)

def remove_rule():
    selected_indices = listbox_rules.curselection()
    if not selected_indices: return
    for index in reversed(selected_indices):
        removed = active_rules[index]
        listbox_rules.delete(index)
        del active_rules[index]
        pipeline_logger.log("rule_removed", rule=removed.get("rule", ""))

def generate_wordlist_via_pipeline():
    profile = {
        "fullname": entry_fullname.get().strip().lower(),
        "birthdate": clean_date(entry_birthdate.get()),
        "relative_name": entry_relative_name.get().strip().lower(),
        "relative_birth": clean_date(entry_relative_birth.get()),
        "child_name": entry_child_name.get().strip().lower(),
        "child_birth": clean_date(entry_child_birth.get()),
        "company": entry_company.get().strip().lower(),
        "hometown": entry_hometown.get().strip().lower(),
    }
    
    wcfrom_str = entry_wcfrom.get().strip()
    wcto_str = entry_wcto.get().strip()
    if not wcfrom_str or not wcto_str:
        messagebox.showerror("Lỗi Đầu Vào", "Vui lòng nhập bộ lọc độ dài.")
        return
    try:
        wcfrom_val, wcto_val = int(wcfrom_str), int(wcto_str)
    except ValueError:
        messagebox.showerror("Lỗi", "Bộ lọc độ dài phải là số.")
        return

    try:
        final_list = rule_executor.generate(active_rules, profile, wcfrom_val, wcto_val)

        if not final_list:
            messagebox.showwarning("Cảnh báo", "Không có kết quả nào sau khi áp dụng các rule và bộ lọc độ dài.")
            return

        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        fname = profile["fullname"] if profile["fullname"] else "wordlist"
        fname = fname.replace(" ", "_").replace("đ", "d")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = os.path.join(output_dir, f"{fname}_{timestamp}.txt")
        
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(final_list) + "\n")

        special_counts = dict(sorted(Counter(count_specials(pw) for pw in final_list).items()))
        summary_path = Path(output_filename).with_suffix(".summary.json")
        summary_path.write_text(json.dumps({
            "total": len(final_list),
            "min_length": min(map(len, final_list)),
            "max_length": max(map(len, final_list)),
            "special_character_counts": special_counts,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        count_text = "\n".join(f"  {n} ký tự đặc biệt: {total} dòng" for n, total in special_counts.items())

        pipeline_logger.log(
            "pipeline_completed",
            rule_count=len(active_rules),
            output_count=len(final_list),
        )
        messagebox.showinfo("Thành công", f"Pipeline đã hoàn tất với {len(final_list)} kết quả.\n\n{count_text}\n\nFile txt: {os.path.abspath(output_filename)}\nThống kê: {summary_path.name}")
        
    except RuleValidationError as exc:
        messagebox.showerror("Cấu hình không hợp lệ", str(exc))
    except Exception as e:
        messagebox.showerror("Lỗi hệ thống", f"Lỗi khi chạy bộ sinh: {str(e)}")

# ==========================================
# XÂY DỰNG GIAO DIỆN GUI
# ==========================================
def create_scrollable_frame(parent, width=540):
    """Keep tall analysis/profile panels reachable on small or scaled displays."""
    container = tk.Frame(parent)
    container.pack(fill=tk.BOTH, expand=True)
    container.rowconfigure(0, weight=1)
    container.columnconfigure(0, weight=1)

    canvas = tk.Canvas(container, width=width, height=1, highlightthickness=0)
    canvas.grid(row=0, column=0, sticky="nsew")
    vertical = tk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal = tk.Scrollbar(container, orient=tk.HORIZONTAL, command=canvas.xview)
    horizontal.grid(row=1, column=0, sticky="ew")
    canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

    content = tk.Frame(canvas)
    window_id = canvas.create_window((0, 0), window=content, anchor="nw")

    def update_size(event=None):
        canvas.itemconfigure(window_id, width=max(content.winfo_reqwidth(), canvas.winfo_width()))
        canvas.configure(scrollregion=canvas.bbox("all"))

    content.bind("<Configure>", update_size)
    canvas.bind("<Configure>", update_size)

    def on_mousewheel(event):
        # Text/list widgets keep their own wheel behaviour. Limit this handler
        # to the scrollable area; do not affect the rules panel or ML windows.
        if event.widget.winfo_class() in {"Text", "Listbox", "TCombobox", "Spinbox"}:
            return
        widget = event.widget
        while widget is not None and widget is not container:
            widget = widget.master
        if widget is None:
            return
        if getattr(event, "num", None) in (4, 5):
            steps = -1 if event.num == 4 else 1
        elif getattr(event, "delta", 0):
            steps = -int(event.delta / 120) if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1)
        else:
            return
        canvas.yview_scroll(steps, "units")
        return "break"

    top = parent.winfo_toplevel()
    for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        top.bind(sequence, on_mousewheel, add="+")
    return content


def build_gui():
    global root, combo_rule, entry_params, listbox_rules, lbl_leak_status, txt_pattern_preview
    global entry_pattern_top, entry_pattern_min_count, lbl_pattern_metrics
    global entry_fullname, entry_birthdate, entry_relative_name, entry_relative_birth
    global entry_child_name, entry_child_birth, entry_company, entry_hometown
    global entry_wcfrom, entry_wcto
    global frame_random_params, lbl_rule_description
    global entry_random_min, entry_random_max, entry_random_count, combo_random_position
    global txt_core_analysis, lbl_core_ai_status
    global frame_special_params, frame_special_counts, special_count_rows
    global entry_special_characters, combo_special_position, entry_special_samples
    root = tk.Tk()
    root.title("pass_ai v4 — Password Strength ML Lab")
    width = max(1, min(1030, root.winfo_screenwidth() - 40))
    height = max(1, min(800, root.winfo_screenheight() - 100))
    root.geometry(f"{width}x{height}")
    root.minsize(min(760, width), min(420, height))

    left_frame = tk.Frame(root)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Reserve footer space BEFORE packing the expandable content. Otherwise
    # the tall analysis panels consume the available height and hide the filter.
    frame_config = tk.LabelFrame(left_frame, text="Bộ lọc độ dài", padx=10, pady=10)
    frame_config.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
    scroll_content = create_scrollable_frame(left_frame)

    # KHỐI PHÂN TÍCH THỐNG KÊ TỔNG HỢP
    frame_ai = tk.LabelFrame(
        scroll_content,
        text="🧠 Phân tích cấu trúc mật khẩu (Aggregate Pattern Lab)",
        padx=10,
        pady=10,
        bg="#f0f8ff",
    )
    frame_ai.pack(fill=tk.X, pady=5)

    btn_load = tk.Button(
        frame_ai,
        text="📊 Nạp Dataset Được Phép",
        bg="#2196F3",
        fg="white",
        font=("Arial", 9, "bold"),
        command=load_pattern_dataset,
    )
    btn_load.pack(fill=tk.X, pady=2)

    lbl_leak_status = tk.Label(frame_ai, text="Chưa nạp dataset phân tích...", fg="#555", bg="#f0f8ff")
    lbl_leak_status.pack(anchor="w")

    filter_row = tk.Frame(frame_ai, bg="#f0f8ff")
    filter_row.pack(fill=tk.X, pady=(5, 2))
    tk.Label(filter_row, text="Top-N:", bg="#f0f8ff").pack(side=tk.LEFT)
    entry_pattern_top = tk.Entry(filter_row, width=6)
    entry_pattern_top.insert(0, "10")
    entry_pattern_top.pack(side=tk.LEFT, padx=(4, 10))
    tk.Label(filter_row, text="Min count:", bg="#f0f8ff").pack(side=tk.LEFT)
    entry_pattern_min_count = tk.Entry(filter_row, width=6)
    entry_pattern_min_count.insert(0, "1")
    entry_pattern_min_count.pack(side=tk.LEFT, padx=(4, 10))
    tk.Button(filter_row, text="Làm mới", command=refresh_pattern_preview).pack(side=tk.LEFT)

    lbl_pattern_metrics = tk.Label(
        frame_ai,
        text="Mẫu: 0 | Pattern: 0 | Độ dài TB: 0 | Coverage: 0%",
        fg="#333",
        bg="#f0f8ff",
        anchor="w",
        justify=tk.LEFT,
    )
    lbl_pattern_metrics.pack(fill=tk.X, pady=(2, 2))

    txt_pattern_preview = tk.Text(frame_ai, height=7, width=56, font=("Consolas", 8), state=tk.DISABLED)
    txt_pattern_preview.pack(fill=tk.X, pady=(4, 4))

    export_row = tk.Frame(frame_ai, bg="#f0f8ff")
    export_row.pack(fill=tk.X)
    tk.Button(export_row, text="Xuất JSON", command=export_pattern_json).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
    tk.Button(export_row, text="Xuất CSV", command=export_pattern_csv).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

    frame_core_ai = tk.LabelFrame(
        frame_ai,
        text="🤖 AI đọc cách sinh trong lõi cơ học",
        padx=6,
        pady=6,
        bg="#f0f8ff",
    )
    frame_core_ai.pack(fill=tk.X, pady=(6, 0))
    lbl_core_ai_status = tk.Label(
        frame_core_ai,
        text="Chưa đọc mã nguồn lõi.",
        fg="#555",
        bg="#f0f8ff",
        anchor="w",
    )
    lbl_core_ai_status.pack(fill=tk.X)
    core_ai_buttons = tk.Frame(frame_core_ai, bg="#f0f8ff")
    core_ai_buttons.pack(fill=tk.X, pady=2)
    tk.Button(
        core_ai_buttons,
        text="Đọc lại handle.py",
        command=show_core_ai_analysis,
    ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
    txt_core_analysis = tk.Text(
        frame_core_ai,
        height=8,
        width=56,
        font=("Consolas", 8),
        state=tk.DISABLED,
    )
    txt_core_analysis.pack(fill=tk.X, pady=(3, 0))

    tk.Button(frame_ai, text="🤖 Mở cửa sổ ML: Huấn luyện / Kiểm định / Giải thích",
              command=open_strength_window).pack(fill=tk.X, pady=(5, 0))

    # KHÔI PHỤC ĐẦY ĐỦ THÔNG TIN NGƯỜI DÙNG
    frame_profile = tk.LabelFrame(scroll_content, text="Thông tin người dùng (Phôi dữ liệu)", padx=10, pady=10)
    frame_profile.pack(fill=tk.X, pady=5)

    tk.Label(frame_profile, text="Họ và tên:").grid(row=0, column=0, sticky="w")
    entry_fullname = tk.Entry(frame_profile, width=30)
    entry_fullname.bind("<FocusOut>", validate_name_field)
    entry_fullname.grid(row=0, column=1, padx=5, pady=2)

    tk.Label(frame_profile, text="Sinh nhật (VD: 06/08/1980):").grid(row=1, column=0, sticky="w")
    entry_birthdate = tk.Entry(frame_profile, width=30)
    entry_birthdate.bind("<FocusOut>", make_date_validator(entry_birthdate))
    entry_birthdate.grid(row=1, column=1, padx=5, pady=2)

    tk.Label(frame_profile, text="Người thân:").grid(row=2, column=0, sticky="w")
    entry_relative_name = tk.Entry(frame_profile, width=30)
    entry_relative_name.bind("<FocusOut>", validate_name_field)
    entry_relative_name.grid(row=2, column=1, padx=5, pady=2)

    tk.Label(frame_profile, text="Sinh nhật (Nhập khuyết 06/08):").grid(row=3, column=0, sticky="w")
    entry_relative_birth = tk.Entry(frame_profile, width=30)
    entry_relative_birth.bind("<FocusOut>", make_date_validator(entry_relative_birth))
    entry_relative_birth.grid(row=3, column=1, padx=5, pady=2)

    tk.Label(frame_profile, text="Con cái:").grid(row=4, column=0, sticky="w")
    entry_child_name = tk.Entry(frame_profile, width=30)
    entry_child_name.bind("<FocusOut>", validate_name_field)
    entry_child_name.grid(row=4, column=1, padx=5, pady=2)

    tk.Label(frame_profile, text="Sinh nhật (Nhập khuyết 08/1980):").grid(row=5, column=0, sticky="w")
    entry_child_birth = tk.Entry(frame_profile, width=30)
    entry_child_birth.bind("<FocusOut>", make_date_validator(entry_child_birth))
    entry_child_birth.grid(row=5, column=1, padx=5, pady=2)

    tk.Label(frame_profile, text="Nơi làm việc:").grid(row=6, column=0, sticky="w")
    entry_company = tk.Entry(frame_profile, width=30)
    entry_company.grid(row=6, column=1, padx=5, pady=2)

    tk.Label(frame_profile, text="Quê quán:").grid(row=7, column=0, sticky="w")
    entry_hometown = tk.Entry(frame_profile, width=30)
    entry_hometown.grid(row=7, column=1, padx=5, pady=2)

    # KHUNG BỘ LỌC ĐỘ DÀI
    tk.Label(frame_config, text="Từ (wcfrom):").grid(row=0, column=0, sticky="w")
    entry_wcfrom = tk.Entry(frame_config, width=10)
    entry_wcfrom.grid(row=0, column=1, padx=5, pady=2)

    tk.Label(frame_config, text="Đến (wcto):").grid(row=1, column=0, sticky="w")
    entry_wcto = tk.Entry(frame_config, width=10)
    entry_wcto.grid(row=1, column=1, padx=5, pady=2)

    btn_generate = tk.Button(
        frame_config,
        text="🔥 SINH TỪ ĐIỂN",
        bg="#4CAF50",
        fg="white",
        font=("Arial", 9, "bold"),
        command=generate_wordlist_via_pipeline,
    )
    btn_generate.grid(row=0, column=2, rowspan=2, padx=(18, 0), sticky="nsew")

    right_frame = tk.Frame(root)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
    right_content = create_scrollable_frame(right_frame, width=340)

    frame_pipeline = tk.LabelFrame(right_content, text="Xây dựng Pipeline (Rules)", padx=10, pady=10)
    frame_pipeline.pack(fill=tk.BOTH, expand=True)

    frame_add_rule = tk.Frame(frame_pipeline)
    frame_add_rule.pack(fill=tk.X, pady=5)

    tk.Label(frame_add_rule, text="Loại Rule:").grid(row=0, column=0, sticky="w")
    combo_rule = ttk.Combobox(frame_add_rule, values=get_available_rule_names(), width=24, state="readonly")
    combo_rule.set("LÕI_CƠ_HỌC")
    combo_rule.grid(row=0, column=1, padx=5, pady=2)
    combo_rule.bind("<<ComboboxSelected>>", on_rule_selected)

    tk.Label(frame_add_rule, text="Tham số:").grid(row=1, column=0, sticky="w")
    entry_params = tk.Entry(frame_add_rule, width=25)
    entry_params.grid(row=1, column=1, padx=5, pady=2)

    lbl_rule_description = tk.Label(frame_add_rule, wraplength=300, justify=tk.LEFT, fg="#555")
    lbl_rule_description.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 6))

    frame_random_params = tk.LabelFrame(frame_add_rule, text="Cấu hình ghép số ngẫu nhiên", padx=6, pady=6)
    frame_random_params.grid(row=3, column=0, columnspan=2, sticky="ew", pady=4)
    tk.Label(frame_random_params, text="Số chữ số từ:").grid(row=0, column=0, sticky="w")
    entry_random_min = tk.Spinbox(frame_random_params, from_=1, to=8, width=5)
    entry_random_min.delete(0, tk.END)
    entry_random_min.insert(0, str(RANDOM_DEFAULTS["min_digits"]))
    entry_random_min.grid(row=0, column=1, padx=4, pady=2, sticky="w")
    tk.Label(frame_random_params, text="đến:").grid(row=0, column=2, sticky="w")
    entry_random_max = tk.Spinbox(frame_random_params, from_=1, to=8, width=5)
    entry_random_max.delete(0, tk.END)
    entry_random_max.insert(0, str(RANDOM_DEFAULTS["max_digits"]))
    entry_random_max.grid(row=0, column=3, padx=4, pady=2)
    tk.Label(frame_random_params, text="Số mẫu / độ dài:").grid(row=1, column=0, sticky="w")
    entry_random_count = tk.Spinbox(frame_random_params, from_=1, to=100, width=5)
    entry_random_count.delete(0, tk.END)
    entry_random_count.insert(0, str(RANDOM_DEFAULTS["count"]))
    entry_random_count.grid(row=1, column=1, padx=4, pady=2, sticky="w")
    tk.Label(frame_random_params, text="Vị trí ghép:").grid(row=2, column=0, sticky="w")
    combo_random_position = ttk.Combobox(
        frame_random_params, values=list(RANDOM_POSITIONS), width=17, state="readonly"
    )
    combo_random_position.set("Cả trước và sau")
    combo_random_position.grid(row=2, column=1, columnspan=3, padx=4, pady=2, sticky="w")
    tk.Label(
        frame_random_params,
        text="Mẫu tính cho mỗi biến thể tên/địa danh.\nVí dụ: long482, 57hanoi, congtyabc906.\nBấm Thêm Luật để áp dụng; xóa luật để tắt.",
        justify=tk.LEFT, wraplength=290, fg="#555",
    ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(5, 0))

    frame_special_params = tk.LabelFrame(frame_add_rule, text="Số ký tự đặc biệt", padx=6, pady=6)
    frame_special_params.grid(row=3, column=0, columnspan=2, sticky="ew", pady=4)
    counts_header = tk.Frame(frame_special_params)
    counts_header.pack(fill=tk.X)
    tk.Label(counts_header, text="Các nhóm số lượng:").pack(side=tk.LEFT)
    tk.Button(counts_header, text="+", width=3, command=add_special_count_row).pack(side=tk.RIGHT)
    frame_special_counts = tk.Frame(frame_special_params)
    frame_special_counts.pack(fill=tk.X)
    special_count_rows = []
    add_special_count_row(1)

    options = tk.Frame(frame_special_params)
    options.pack(fill=tk.X, pady=(6, 0))
    tk.Label(options, text="Ký tự được phép:").grid(row=0, column=0, sticky="w")
    entry_special_characters = tk.Entry(options, width=19)
    entry_special_characters.insert(0, SPECIAL_DEFAULTS["characters"])
    entry_special_characters.grid(row=0, column=1, sticky="w", padx=4, pady=2)
    tk.Label(options, text="Vị trí:").grid(row=1, column=0, sticky="w")
    combo_special_position = ttk.Combobox(options, values=list(SPECIAL_POSITIONS), width=18, state="readonly")
    combo_special_position.set("Ưu tiên đầu/cuối")
    combo_special_position.grid(row=1, column=1, sticky="w", padx=4, pady=2)
    tk.Label(options, text="Tối đa mẫu mỗi\nnhóm/chuỗi nền:", justify=tk.LEFT).grid(row=2, column=0, sticky="w")
    entry_special_samples = tk.Spinbox(options, from_=1, to=100, width=6)
    entry_special_samples.delete(0, tk.END)
    entry_special_samples.insert(0, str(SPECIAL_DEFAULTS["samples"]))
    entry_special_samples.grid(row=2, column=1, sticky="w", padx=4, pady=2)
    tk.Label(frame_special_params,
             text="Ví dụ chọn 2, bấm + thêm 1 hoặc 3.\nĐếm tổng số dấu, kể cả _ và dấu lặp.\nLuật áp dụng cuối; chỉ xuất các nhóm đã chọn.\nBấm Thêm / Cập nhật luật để áp dụng.",
             wraplength=295, justify=tk.LEFT, fg="#555").pack(anchor="w", pady=(5, 0))

    btn_add_rule = tk.Button(frame_add_rule, text="➕ Thêm / Cập nhật luật", command=add_rule)
    btn_add_rule.grid(row=4, column=0, columnspan=2, pady=5, sticky="ew")

    tk.Label(frame_pipeline, text="Trình tự thực thi:").pack(anchor="w", pady=(10,0))
    listbox_rules = tk.Listbox(frame_pipeline, selectmode=tk.EXTENDED, height=15)
    listbox_rules.pack(fill=tk.BOTH, expand=True, pady=5)
    rules_scroll = tk.Scrollbar(frame_pipeline, orient=tk.HORIZONTAL, command=listbox_rules.xview)
    rules_scroll.pack(fill=tk.X)
    listbox_rules.config(xscrollcommand=rules_scroll.set)

    btn_del_rule = tk.Button(frame_pipeline, text="❌ Xóa Luật đã chọn", command=remove_rule)
    btn_del_rule.pack(fill=tk.X)

    def init_default_rules():
        active_rules.clear()
        combo_rule.set("LÕI_CƠ_HỌC")
        on_rule_selected()
        add_rule()

    init_default_rules()
    return root


if __name__ == "__main__":
    app = build_gui()
    app.mainloop()
