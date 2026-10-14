#!/usr/bin/env python3
import configparser
import os
import re
import unicodedata
import itertools
from itertools import combinations, product
from datetime import datetime

# Global configuration dictionary
CONFIG = {}

leet_map = {
    'a': ['4', '@'],
    'e': ['3'],
    'i': ['1', '!'],
    'o': ['0'],
    's': ['5', '$'],
    't': ['7']
}

def read_config(filename):
    """
    Read configuration file if exists, else use default values.
    """
    CONFIG["min_leet_changes"] = 0
    CONFIG["max_leet_changes"] = 2
    CONFIG["boundary_chars"] = ["!", "@", "#", "$", "%"]
    
    # Đã bổ sung thêm các ký tự & * % @ vào làm dấu phân cách (Separator)
    CONFIG["separator_chars"] = ["_", "-", "@", "*", "&", "%", "$"]
    
    # Only a character set remains; no manually assigned weights.
    CONFIG["additional_special_chars"] = ["+", "."]
    CONFIG["salt"] = ""
    CONFIG["seed"] = 12345

    CONFIG["leet"] = leet_map.copy()

    config = configparser.ConfigParser(interpolation=None)
    config_path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(config_path):
        return

    try:
        config.read(config_path, encoding='utf-8')
    except configparser.Error as e:
        print(f"[!] Cảnh báo: không đọc được '{filename}' ({e}). Dùng cấu hình mặc định.")
        return

    if config.has_section("specialchars") and config.has_option("specialchars", "chars"):
        CONFIG["boundary_chars"] = [x.strip() for x in config.get("specialchars", "chars").split(",")]

    if config.has_section("leet"):
        leet_cfg = {}
        for k, v in config.items("leet"):
            leet_cfg[k] = [x.strip() for x in v.split(",")]
        CONFIG["leet"] = leet_cfg
        
    if config.has_section("leet_options"):
        CONFIG["min_leet_changes"] = config.getint("leet_options", "min_changes", fallback=CONFIG.get("min_leet_changes", 0))
        CONFIG["max_leet_changes"] = config.getint("leet_options", "max_changes", fallback=2)    

    if config.has_section("patterns"):
        if config.has_option("patterns","suffixes"):
            CONFIG["suffixes"] = [x.strip() for x in config.get("patterns", "suffixes").split(",")]
        if config.has_option("patterns","prefixes"):
            CONFIG["prefixes"] = [x.strip() for x in config.get("patterns", "prefixes").split(",")]

    if config.has_section("separators") and config.has_option("separators", "chars"):
        CONFIG["separator_chars"] = [x.strip() for x in config.get("separators", "chars").split(",")]

    if config.has_section("random"):
        CONFIG["salt"] = config.get("random", "salt", fallback=CONFIG.get("salt", ""))
        CONFIG["seed"] = config.getint("random", "seed", fallback=CONFIG.get("seed", 12345))

def configured_special_chars(separator_chars=None):
    chars = set(CONFIG.get("boundary_chars", []))
    chars.update(separator_chars or CONFIG.get("separator_chars", []))
    chars.update(CONFIG.get("additional_special_chars", []))
    return {c for c in chars if c}

def count_separators(text, separator_chars=None):
    sep_list = [s for s in (separator_chars or CONFIG.get("separator_chars", ["_", "-"])) if s]
    return sum(text.count(s) for s in sep_list)

def has_special(text, separator_chars=None):
    specials = configured_special_chars(separator_chars)
    return any(c in specials for c in text)

def remove_vietnamese_in_dictionary(text):
    text = text.replace("Đ", "D").replace("đ", "d")
    nfkd = unicodedata.normalize('NFKD', text)
    return nfkd.encode('ASCII','ignore').decode('ASCII')

def normalize_word(value):
    if not value:
        return ""
    return remove_vietnamese_in_dictionary(value.strip()).replace(" ", "")

def generate_leet_variants(word, min_changes=None, max_changes=None):
    if max_changes is None:
        max_changes = CONFIG.get("max_leet_changes", 2)
    if min_changes is None:
        min_changes = CONFIG.get("min_leet_changes", 0)

    variants = set()
    if min_changes <= 0:
        variants.add(word)

    candidates = [(idx, ch.lower()) for idx, ch in enumerate(word) if ch.lower() in CONFIG.get("leet", {})]

    max_changes = min(max_changes, len(candidates))
    min_changes = max(min_changes, 1) if candidates else 0

    for k in range(min_changes, max_changes + 1):
        if k == 0: continue
        for combo_positions in combinations(candidates, k):
            repl_lists = [CONFIG["leet"][ch] for _, ch in combo_positions]
            for repl_combo in product(*repl_lists):
                new = list(word)
                for (idx, _ch), repl in zip(combo_positions, repl_combo):
                    new[idx] = repl
                variants.add("".join(new))

    return variants

def _parse_flexible_date(date_str):
    """Parse compact dates accepted by the GUI.

    Supported forms after GUI cleaning:
    - DDMMYYYY (8 digits)
    - MMYYYY (6 digits)
    - DDMM (4 digits)
    """
    value = (date_str or "").strip()
    if not value.isdigit():
        return {}

    now = datetime.now()
    try:
        if len(value) == 8:
            dt = datetime.strptime(value, "%d%m%Y")
            if dt.date() > now.date():
                return {}
            return {"dd": dt.strftime("%d"), "mm": dt.strftime("%m"), "yyyy": dt.strftime("%Y"), "yy": dt.strftime("%y")}
        if len(value) == 6:
            dt = datetime.strptime("01" + value, "%d%m%Y")
            if dt.replace(day=1).date() > now.replace(day=1).date():
                return {}
            return {"mm": dt.strftime("%m"), "yyyy": dt.strftime("%Y"), "yy": dt.strftime("%y")}
        if len(value) == 4:
            dt = datetime.strptime(value + "2000", "%d%m%Y")
            return {"dd": dt.strftime("%d"), "mm": dt.strftime("%m")}
    except ValueError:
        return {}
    return {}

def generate_date_variants(date_str):
    """Generate only complete, meaningful date blocks from flexible input."""
    info = _parse_flexible_date(date_str)
    if not info:
        return set()

    variants = set()
    dd = info.get("dd")
    mm = info.get("mm")
    yyyy = info.get("yyyy")
    yy = info.get("yy")

    if yyyy:
        variants.add(yyyy)
    if yy:
        variants.add(yy)
    if dd and mm:
        variants.update({dd + mm, mm + dd})
    if dd and mm and yyyy:
        variants.update({dd + mm + yyyy, dd + mm + yy})
    if mm and yyyy and not dd:
        variants.add(mm + yyyy)

    return variants

def apply_common_patterns(word):
    variants = set()
    for s in CONFIG.get("suffixes", []): variants.add(word + s)
    for p in CONFIG.get("prefixes", []): variants.add(p + word)
    return variants

def parse_vietnamese_name(fullname):
    fullname = remove_vietnamese_in_dictionary(fullname)
    fullname = re.sub(r"[-_.]+", " ", fullname)
    tokens = [x.lower() for x in fullname.split() if x]

    if not tokens:
        return None

    if len(tokens) == 1:
        return {"surname": "", "middle": [], "given": tokens[0], "given_full": tokens[0], "variants": [tokens[0]]}

    surname = tokens[0]
    middle = tokens[1:-1]
    given = tokens[-1]
    middle_full = "".join(middle)

    variants = set()
    variants.add(surname)
    variants.add(given)
    variants.add(given + surname)
    variants.add(surname + given)

    if middle_full:
        variants.add(middle_full + given)
        variants.add(surname + middle_full + given)
        variants.add(middle_full + given + surname)

    return {"surname": surname, "middle": middle, "given": given, "given_full": middle_full + given, "variants": list(variants)}

def parse_date_tokens(date_str):
    return _parse_flexible_date(date_str)

def generate_cross_family_dates(profile):
    patterns = set()
    years_yy, days_ddmm = set(), set()

    for field in ["birthdate", "relative_birth", "child_birth"]:
        info = parse_date_tokens(profile.get(field, ""))
        if info.get("yy"):
            years_yy.add(info["yy"])
        if info.get("dd") and info.get("mm"):
            days_ddmm.add(info["dd"] + info["mm"])

    years_yy, days_ddmm = list(years_yy), list(days_ddmm)

    if len(years_yy) >= 2:
        for combo in itertools.permutations(years_yy, 2):
            patterns.add("".join(combo))

    for yy in years_yy:
        for ddmm in days_ddmm:
            patterns.add(yy + ddmm)
            patterns.add(ddmm + yy)

    if len(years_yy) >= 2 and days_ddmm:
        for yy_combo in itertools.permutations(years_yy, 2):
            yy_str = "".join(yy_combo)
            for ddmm in days_ddmm:
                patterns.add(yy_str + ddmm)
                patterns.add(ddmm + yy_str)

    return patterns

def generate_basic_wordlist(profile, wcfrom, wcto):
    words = set()
    forced = set()
    boundary_chars = CONFIG.get("boundary_chars", ["!", "@", "#", "$", "%"])
    separator_chars = CONFIG.get("separator_chars", ["_", "-", "@", "*", "&", "%", "$"])

    # --- HÀM CỐT LÕI: Áp dụng biến thể và gắn ký tự biên (Prefix/Suffix) ---
    def process_and_add(base_str):
        base_str = normalize_word(base_str)
        if not base_str: return

        # 1. Biến thể Hoa/Thường (LÕI CƠ HỌC ĐÃ SẠCH BÓNG LEETSPEAK)
        for var in [base_str, base_str.upper(), base_str.lower(), base_str.title()]:
            var = var.strip()
            if not var: continue
            words.add(var)

        # 2. Gắn Ký tự biên (Boundary: Prefix / Suffix)
        if not has_special(base_str, separator_chars):
            for spec in boundary_chars:
                words.add(spec + base_str)
                words.add(base_str + spec)

        # 3. Hậu tố phổ biến
        words.update(apply_common_patterns(base_str))

        # Lưu vào danh sách bắt buộc (force)
        forced.update([base_str, base_str.upper(), base_str.title()])

    # --- BẮT ĐẦU XỬ LÝ TỪNG THỰC THỂ (Entity) ---
    entities = [
        ("fullname", "birthdate"),
        ("relative_name", "relative_birth"),
        ("child_name", "child_birth")
    ]

    for name_field, date_field in entities:
        if not profile.get(name_field): continue
        info = parse_vietnamese_name(profile[name_field])
        if not info: continue

        # Lấy ngày sinh của CHÍNH NGƯỜI NÀY
        person_date_tokens = set()
        if profile.get(date_field):
            person_date_tokens = generate_date_variants(profile[date_field])

        surname = info.get("surname", "")
        given = info.get("given", "")
        given_full = info.get("given_full", "")
        middle = info.get("middle", [])
        middle_full = "".join(middle)

        # Định nghĩa các khối tên đẹp được phép ghép với ngày tháng
        good_name_blocks = set()
        if given: good_name_blocks.add(given)
        if given_full: good_name_blocks.add(given_full)
        if surname and given:
            good_name_blocks.add(surname + given)
            good_name_blocks.add(given + surname)
        if surname and given_full:
            good_name_blocks.add(surname + given_full)
            good_name_blocks.add(given_full + surname)
        if middle_full and given:
            good_name_blocks.add(middle_full + given)
            if surname:
                good_name_blocks.add(surname + middle_full + given)
                good_name_blocks.add(middle_full + given + surname)

        # Xử lý các biến thể tên đơn lẻ
        for value in info["variants"]:
            process_and_add(value)
            
            # NẾU là khối tên đẹp -> Tiến hành ghép với ngày tháng
            if value in good_name_blocks:
                for token in person_date_tokens:
                    # Ghép trực tiếp: duc05, 05duc
                    process_and_add(value + token)
                    process_and_add(token + value)
                    # Ghép qua dấu phân cách: duc_05, duc@05
                    for sep in separator_chars:
                        if sep:
                            process_and_add(value + sep + token)
                            process_and_add(token + sep + value)

        # Xử lý trường hợp Tên có dấu phân cách (vd: dinh_tuyen)
        if surname:
            for part in [given, given_full]:
                if not part: continue
                for sep in separator_chars:
                    if not sep: continue
                    for sp in [surname + sep + part, part + sep + surname]:
                        # Đẩy khối tên có dấu phân cách qua hàm xử lý
                        process_and_add(sp)
                        
                        # Tiếp tục ghép tên có phân cách này với ngày tháng (dinh_tuyen_80)
                        for token in person_date_tokens:
                            process_and_add(sp + sep + token)
                            process_and_add(token + sep + sp)

    # Các thông tin phụ (công ty, quê quán) được ghép với ngày sinh của User mục tiêu
    # Các thông tin phụ (công ty, quê quán) được ghép với ngày sinh của User mục tiêu
    target_dates = set()
    if profile.get("birthdate"):
        target_dates = generate_date_variants(profile["birthdate"])

    # Trích xuất các phần tên chính (Tên, Tên đệm + Tên, Họ) để chuẩn bị ghép với quê quán
    main_names = set()
    if profile.get("fullname"):
        info = parse_vietnamese_name(profile["fullname"])
        if info:
            if info.get("given"): main_names.add(info["given"])
            if info.get("given_full"): main_names.add(info["given_full"])
            if info.get("surname"): main_names.add(info["surname"])

    for field in ["company", "hometown"]:
        if profile.get(field):
            base_val = normalize_word(profile[field])
            process_and_add(base_val)
            
            # 1. Ghép với SỐ (Ngày sinh) có và không có ký tự phân cách
            for token in target_dates:
                process_and_add(base_val + token)
                process_and_add(token + base_val)
                for sep in separator_chars:
                    if sep:
                        process_and_add(base_val + sep + token)
                        process_and_add(token + sep + base_val)
            
            # 2. Ghép với TÊN có và không có ký tự phân cách
            for name_val in main_names:
                process_and_add(base_val + name_val)
                process_and_add(name_val + base_val)
                for sep in separator_chars:
                    if sep:
                        process_and_add(base_val + sep + name_val)
                        process_and_add(name_val + sep + base_val)
                        
                        # 3. Ghép tổ hợp: TÊN + KÝ TỰ + QUÊ QUÁN + KÝ TỰ + SỐ (VD: hung_hn_1980)
                        for token in target_dates:
                            process_and_add(name_val + sep + base_val + sep + token)
                            process_and_add(base_val + sep + name_val + sep + token)

    # In ra tất cả ngày tháng độc lập
    for field in ["birthdate", "relative_birth", "child_birth"]:
        if profile.get(field):
            for dv in generate_date_variants(profile[field]):
                process_and_add(dv)

    # Ghép chéo ngày tháng gia đình (như 8085, 1980_1985)
    cross_dates = generate_cross_family_dates(profile)
    for cd in cross_dates:
        process_and_add(cd)

    def password_filter(pwd):
        # Nới lỏng một chút: Các chuỗi dài hơn (Tên + Ký tự ghép + Ngày) đôi khi có thể cần tới 3 separator
        if count_separators(pwd, separator_chars) > 3: return False
        for sep in separator_chars:
            if sep and (sep + sep in pwd):
                return False
        if "__" in pwd or "--" in pwd or "_-" in pwd or "-_" in pwd: return False
        return True

    candidates = sorted({pw for pw in words | forced if password_filter(pw) and wcfrom <= len(pw) <= wcto})

    # Core generation is deterministic and does not decide popularity.
    # Statistical prevalence/ranking belongs to PatternFrequencyModel.
    return candidates