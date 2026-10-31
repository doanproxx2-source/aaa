import sqlite3
import shutil
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
import pypinyin

DB_NAME = "translator_pro.db"

# Danh sách các chủ đề mặc định cũ cần tự động dọn sạch khỏi menu
OLD_DEFAULT_TOPICS_TO_REMOVE = [
    "Giao tiếp hàng ngày",
    "Công việc",
    "Nhà máy",
    "Điện công nghiệp",
    "Tự động hóa",
    "PLC",
    "Machine Vision",
    "SMT",
    "AOI",
    "ICT",
    "Bảo trì máy móc",
    "Kinh doanh và giao hàng",
    "abc"
]

DEFAULT_CAMVISION_DATA = [
    ("机器视觉", "jīqì shìjué", "cơ khí thị giác", "thị giác máy", "机器视觉可以自动检测产品。", "Jīqì shìjué kěyǐ zìdòng jiǎncè chǎnpǐn.", "Thị giác máy có thể tự động kiểm tra sản phẩm.", "abc", "Camvision"),
    ("视觉", "shìjué", "thị giác", "thị giác; liên quan đến mắt", "这个视觉系统可以检测产品。", "Zhège shìjué xìtǒng kěyǐ jiǎncè chǎnpǐn.", "Hệ thống thị giác này có thể kiểm tra sản phẩm.", "abc", "Camvision"),
    ("视觉系统", "shìjué xìtǒng", "thị giác hệ thống", "hệ thống thị giác", "这个视觉系统主要用来检测产品。", "Zhège shìjué xìtǒng zhǔyào yònglái jiǎncè chǎnpǐn.", "Hệ thống thị giác này chủ yếu dùng để kiểm tra sản phẩm.", "abc", "Camvision"),
    ("相机", "xiàngjī", "tương cơ", "camera", "相机的位置需要调整。", "Xiàngjī de wèizhi xūyào tiáozhěng.", "Vị trí camera cần được điều chỉnh.", "abc", "Camvision"),
    ("工业相机", "gōngyè xiàngjī", "công nghiệp tương cơ", "camera công nghiệp", "这台设备使用的是工业相机。", "Zhè tái shèbèi shǐyòng de shì gōngyè xiàngjī.", "Thiết bị này sử dụng camera công nghiệp.", "abc", "Camvision"),
    ("镜头", "jìngtóu", "kính đầu", "ống kính", "镜头太脏会影响图像质量。", "Jìngtóu tài zāng huì yǐngxiǎng túxiàng zhìliàng.", "Ống kính quá bẩn sẽ ảnh hưởng chất lượng hình ảnh.", "abc", "Camvision"),
    ("光源", "guāngyuán", "quang nguyên", "nguồn sáng", "光源的亮度需要调整。", "Guāngyuán de liàngdù xūyào tiáozhěng.", "Độ sáng của nguồn sáng cần được điều chỉnh.", "abc", "Camvision"),
    ("光纤", "guāngxiān", "quang tiêm", "sợi quang, ánh sáng", "光纤连接好了以后再测试。", "Guāngxiān liánjiē hǎo le yǐhòu zài cèshì.", "Sau khi kết nối sợi quang xong thì kiểm tra lại.", "abc", "Camvision"),
    ("照明", "zhàomíng", "chiếu minh", "chiếu sáng", "照明不好会影响检测结果。", "Zhàomíng bù hǎo huì yǐngxiǎng jiǎncè jiéguǒ.", "Chiếu sáng không tốt sẽ ảnh hưởng kết quả kiểm tra.", "abc", "Camvision"),
    ("图片", "túpiàn", "đồ phiến", "hình ảnh", "这张图片有点模糊。", "Zhè zhāng túpiàn yǒudiǎn móhu.", "Hình ảnh này hơi mờ.", "abc", "Camvision"),
    ("测试运行", "cèshì yùnxíng", "trắc thí vận hành", "chạy thử, vận hành kiểm tra", "修改参数后，进行测试运行。", "Xiūgǎi cānshù hòu, jìnxíng cèshì yùnxíng.", "Sau khi sửa tham số, tiến hành chạy thử.", "abc", "Camvision"),
]


def get_connection():
    return sqlite3.connect(DB_NAME)


def _auto_pinyin(text: str) -> str:
    if not text:
        return ""
    res = pypinyin.pinyin(text, style=pypinyin.Style.TONE)
    return " ".join([item[0] for item in res])


def clean_meaning_text(meaning: str) -> str:
    if not meaning:
        return ""
    return meaning.split("|")[0].strip()


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_text TEXT,
            target_text TEXT,
            source_lang TEXT,
            target_lang TEXT,
            direction TEXT,
            mode TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            pinyin TEXT,
            hanviet TEXT,
            pos TEXT,
            meaning TEXT,
            zh_meaning TEXT,
            hsk TEXT,
            examples TEXT,
            example_zh TEXT DEFAULT '',
            example_pinyin TEXT DEFAULT '',
            example_vi TEXT DEFAULT '',
            topic TEXT DEFAULT 'Camvision',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grammar_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sentence TEXT UNIQUE,
            pinyin TEXT,
            meaning TEXT,
            analysis_result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_name TEXT UNIQUE
        )
    """)

    cursor.execute("PRAGMA table_info(saved_vocabulary)")
    vocab_cols = [col[1] for col in cursor.fetchall()]
    for col_name, default_val in [
        ("zh_meaning", "''"),
        ("examples", "''"),
        ("example_zh", "''"),
        ("example_pinyin", "''"),
        ("example_vi", "''"),
        ("topic", "'Camvision'")
    ]:
        if col_name not in vocab_cols:
            cursor.execute(f"ALTER TABLE saved_vocabulary ADD COLUMN {col_name} TEXT DEFAULT {default_val}")

    # Xóa tự động các chủ đề mặc định cũ gây rối mắt (Tự động hóa, PLC, Giao tiếp hàng ngày, abc...)
    for old_t in OLD_DEFAULT_TOPICS_TO_REMOVE:
        cursor.execute("DELETE FROM custom_topics WHERE topic_name = ?", (old_t,))
        cursor.execute("UPDATE saved_vocabulary SET topic = 'Camvision' WHERE topic = ?", (old_t,))

    # Đảm bảo có ít nhất 1 chủ đề Camvision nếu danh sách trống
    cursor.execute("SELECT COUNT(*) FROM custom_topics")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT OR IGNORE INTO custom_topics (topic_name) VALUES ('Camvision')")

    # Chỉ nạp bộ từ Camvision mẫu nếu bảng từ vựng đang hoàn toàn trống
    cursor.execute("SELECT COUNT(*) FROM saved_vocabulary")
    if cursor.fetchone()[0] == 0:
        _seed_default_camvision(cursor)

    conn.commit()
    conn.close()


def _seed_default_camvision(cursor):
    cursor.execute("INSERT OR IGNORE INTO custom_topics (topic_name) VALUES ('Camvision')")
    for w, py, hv, m, ex_z, ex_p, ex_v, lvl, folder in DEFAULT_CAMVISION_DATA:
        full_ex = f"{ex_z}\n{ex_p}\n{ex_v}"
        cursor.execute("""
            INSERT OR IGNORE INTO saved_vocabulary (
                word, pinyin, hanviet, pos, meaning, hsk,
                examples, example_zh, example_pinyin, example_vi, topic
            )
            VALUES (?, ?, ?, 'Từ vựng', ?, ?, ?, ?, ?, ?, ?)
        """, (w, py, hv, m, lvl, full_ex, ex_z, ex_p, ex_v, folder))


# ================= KHÔI PHỤC MẶC ĐỊNH / XÓA SẠCH DỮ LIỆU =================
def reset_all_data(keep_sample_camvision: bool = False):
    """Xóa toàn bộ dữ liệu từ vựng, chủ đề, lịch sử dịch và lịch sử ngữ pháp."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM translation_history")
    cursor.execute("DELETE FROM grammar_history")
    cursor.execute("DELETE FROM saved_vocabulary")
    cursor.execute("DELETE FROM custom_topics")

    cursor.execute("INSERT OR IGNORE INTO custom_topics (topic_name) VALUES ('Camvision')")
    if keep_sample_camvision:
        _seed_default_camvision(cursor)

    conn.commit()
    conn.close()


# ================= QUẢN LÝ CHỦ ĐỀ / FOLDER =================
def get_all_topics() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT topic_name FROM custom_topics ORDER BY id ASC")
    topics = [r[0] for r in cursor.fetchall() if r[0]]

    cursor.execute("SELECT DISTINCT topic FROM saved_vocabulary WHERE topic IS NOT NULL AND topic != ''")
    for r in cursor.fetchall():
        t_name = r[0].strip()
        if t_name and t_name not in topics and t_name not in OLD_DEFAULT_TOPICS_TO_REMOVE:
            topics.append(t_name)
            cursor.execute("INSERT OR IGNORE INTO custom_topics (topic_name) VALUES (?)", (t_name,))

    conn.commit()
    conn.close()
    return topics if topics else ["Camvision"]


def add_custom_topic(topic_name: str) -> bool:
    topic_name = topic_name.strip()
    if not topic_name:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO custom_topics (topic_name) VALUES (?)", (topic_name,))
    conn.commit()
    conn.close()
    return True


def delete_custom_topic(topic_name: str, delete_words_inside: bool = False):
    topic_name = topic_name.strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_topics WHERE topic_name = ?", (topic_name,))
    if delete_words_inside:
        cursor.execute("DELETE FROM saved_vocabulary WHERE topic = ?", (topic_name,))
    else:
        cursor.execute("UPDATE saved_vocabulary SET topic = 'Camvision' WHERE topic = ?", (topic_name,))
        cursor.execute("INSERT OR IGNORE INTO custom_topics (topic_name) VALUES ('Camvision')")
    conn.commit()
    conn.close()


# ================= QUẢN LÝ LỊCH SỬ DỊCH =================
def save_translation(source, target, source_lang="", target_lang="", direction="Tự động", mode="Tự động"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO translation_history (source_text, target_text, source_lang, target_lang, direction, mode)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (source, target, source_lang, target_lang, direction, mode))
    conn.commit()
    conn.close()


def get_history(search_query="", limit=100):
    conn = get_connection()
    cursor = conn.cursor()
    if search_query.strip():
        q = f"%{search_query.strip()}%"
        cursor.execute("""
            SELECT id, source_text, target_text, source_lang, target_lang, mode, created_at
            FROM translation_history
            WHERE source_text LIKE ? OR target_text LIKE ?
            ORDER BY id DESC LIMIT ?
        """, (q, q, limit))
    else:
        cursor.execute("""
            SELECT id, source_text, target_text, source_lang, target_lang, mode, created_at
            FROM translation_history
            ORDER BY id DESC LIMIT ?
        """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_history_item(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM translation_history WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def clear_all_history():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM translation_history")
    conn.commit()
    conn.close()


# ================= QUẢN LÝ CÂU PHÂN TÍCH NGỮ PHÁP =================
def save_grammar_sentence(sentence, pinyin, meaning, analysis_result):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO grammar_history (sentence, pinyin, meaning, analysis_result)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(sentence) DO UPDATE SET
            pinyin=excluded.pinyin,
            meaning=excluded.meaning,
            analysis_result=excluded.analysis_result,
            created_at=CURRENT_TIMESTAMP
    """, (sentence.strip(), pinyin, meaning, analysis_result))
    conn.commit()
    conn.close()


def get_saved_grammar(search_query="", limit=100):
    conn = get_connection()
    cursor = conn.cursor()
    if search_query.strip():
        q = f"%{search_query.strip()}%"
        cursor.execute("""
            SELECT id, sentence, pinyin, meaning, analysis_result, created_at
            FROM grammar_history
            WHERE sentence LIKE ? OR meaning LIKE ?
            ORDER BY id DESC LIMIT ?
        """, (q, q, limit))
    else:
        cursor.execute("""
            SELECT id, sentence, pinyin, meaning, analysis_result, created_at
            FROM grammar_history
            ORDER BY id DESC LIMIT ?
        """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_grammar_item(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM grammar_history WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def clear_all_grammar():
    """Xóa toàn bộ các câu ngữ pháp đã lưu."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM grammar_history")
    conn.commit()
    conn.close()


# ================= QUẢN LÝ SỔ TỪ VỰNG & PHÂN TRANG CHỐNG TREO =================
def save_word(
    word, pinyin, hanviet, pos, meaning,
    zh_meaning="", hsk="abc", examples="",
    topic="Camvision", notes="",
    example_zh="", example_pinyin="", example_vi=""
):
    word = str(word).strip()
    if not word:
        return
    meaning = clean_meaning_text(str(meaning))
    topic = str(topic).strip() or "Camvision"

    if not example_zh and examples:
        first_line = examples.split("\n")[0].strip()
        example_zh = first_line.split("(")[0].strip() if "(" in first_line else first_line
        if "→" in first_line:
            example_vi = first_line.split("→")[-1].strip()
        elif "-" in first_line:
            example_vi = first_line.split("-")[-1].strip()
        example_pinyin = _auto_pinyin(example_zh)

    if example_zh and not examples:
        examples = f"{example_zh}\n{example_pinyin}\n{example_vi}"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO custom_topics (topic_name) VALUES (?)", (topic,))
    cursor.execute("""
        INSERT INTO saved_vocabulary (
            word, pinyin, hanviet, pos, meaning, zh_meaning, hsk,
            examples, example_zh, example_pinyin, example_vi, topic, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(word) DO UPDATE SET
            pinyin=excluded.pinyin,
            hanviet=excluded.hanviet,
            pos=excluded.pos,
            meaning=excluded.meaning,
            zh_meaning=excluded.zh_meaning,
            hsk=excluded.hsk,
            examples=excluded.examples,
            example_zh=excluded.example_zh,
            example_pinyin=excluded.example_pinyin,
            example_vi=excluded.example_vi,
            topic=excluded.topic,
            notes=excluded.notes
    """, (
        word, pinyin, hanviet, pos, meaning, zh_meaning, hsk,
        examples, example_zh, example_pinyin, example_vi, topic, notes
    ))
    conn.commit()
    conn.close()


def get_saved_words(search_query="", topic_filter="Tất cả"):
    """Lấy toàn bộ từ (dùng cho Flashcard, Xuất Excel và Nông Trại)."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT id, word, pinyin, hanviet, pos, meaning, hsk, topic,
               examples, notes, created_at, example_zh, example_pinyin, example_vi
        FROM saved_vocabulary WHERE 1=1
    """
    params = []

    if topic_filter and topic_filter != "Tất cả":
        query += " AND topic = ?"
        params.append(topic_filter)

    if search_query.strip():
        q = f"%{search_query.strip()}%"
        query += " AND (word LIKE ? OR pinyin LIKE ? OR hanviet LIKE ? OR meaning LIKE ? OR topic LIKE ?)"
        params.extend([q, q, q, q, q])

    query += " ORDER BY id ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_saved_words_paginated(search_query="", topic_filter="Tất cả", page=1, page_size=20) -> tuple[list, int]:
    """
    Chỉ truy vấn đúng 20 từ của trang hiện tại để giao diện hiển thị tức thì (0.01 giây),
    không bao giờ bị treo dù có 10.000 từ vựng.
    """
    conn = get_connection()
    cursor = conn.cursor()
    where_clause = "WHERE 1=1"
    params = []

    if topic_filter and topic_filter != "Tất cả":
        where_clause += " AND topic = ?"
        params.append(topic_filter)

    if search_query.strip():
        q = f"%{search_query.strip()}%"
        where_clause += " AND (word LIKE ? OR pinyin LIKE ? OR hanviet LIKE ? OR meaning LIKE ? OR topic LIKE ?)"
        params.extend([q, q, q, q, q])

    cursor.execute(f"SELECT COUNT(*) FROM saved_vocabulary {where_clause}", params)
    total_count = cursor.fetchone()[0]

    offset = max(0, (page - 1) * page_size)
    query = f"""
        SELECT id, word, pinyin, hanviet, pos, meaning, hsk, topic,
               examples, notes, created_at, example_zh, example_pinyin, example_vi
        FROM saved_vocabulary {where_clause}
        ORDER BY id ASC LIMIT ? OFFSET ?
    """
    cursor.execute(query, params + [page_size, offset])
    rows = cursor.fetchall()
    conn.close()
    return rows, total_count


def delete_saved_word(word_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM saved_vocabulary WHERE id = ?", (word_id,))
    conn.commit()
    conn.close()


def delete_words_by_topic(topic_filter="Tất cả"):
    conn = get_connection()
    cursor = conn.cursor()
    if topic_filter == "Tất cả":
        cursor.execute("DELETE FROM saved_vocabulary")
    else:
        cursor.execute("DELETE FROM saved_vocabulary WHERE topic = ?", (topic_filter,))
    conn.commit()
    conn.close()


def export_words_to_excel(filepath, topic_filter="Tất cả"):
    words = get_saved_words(topic_filter=topic_filter)
    wb = Workbook()
    ws = wb.active
    ws.title = topic_filter[:28] if topic_filter != "Tất cả" else "Camvision"

    headers = [
        "Word", "Pinyin", "Sino-Vietnamese", "Meaning",
        "Example", "Example Pinyin", "Example Translation", "Level", "Folder"
    ]
    ws.append(headers)

    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for w in words:
        w_id, word, pinyin, hanviet, pos, meaning, hsk, topic, examples, notes, created_at, ex_zh, ex_py, ex_vi = w
        ws.append([
            word,
            pinyin,
            hanviet,
            clean_meaning_text(meaning),
            ex_zh or (examples.split("\n")[0] if examples else ""),
            ex_py or _auto_pinyin(ex_zh),
            ex_vi or "",
            hsk,
            topic
        ])

    column_widths = [16, 20, 20, 28, 36, 36, 38, 10, 16]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + i)].width = width

    wb.save(filepath)


def import_words_from_excel(filepath: str, use_sheet_name_as_folder: bool = False) -> tuple[int, list]:
    """
    Nhập Excel tốc độ cao bằng Batch Transaction (Gộp 1 lần ghi ổ cứng duy nhất),
    chống treo 100% và không để cột Level ('abc') bị nhảy nhầm thành tên Folder.
    """
    wb = load_workbook(filepath, data_only=True)
    imported_count = 0
    added_folders = set()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue

            first_row = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
            start_idx = 1 if any(k in first_row for k in ["word", "từ vựng", "pinyin", "meaning", "nghĩa"]) else 0

            for r in rows[start_idx:]:
                if not r or all(c is None or str(c).strip() == "" for c in r):
                    continue

                if len(first_row) > 1 and first_row[0] == "id":
                    word = str(r[1] or "").strip()
                    pinyin = str(r[2] or "").strip()
                    hanviet = str(r[3] or "").strip()
                    pos = str(r[4] or "Từ vựng").strip()
                    meaning = clean_meaning_text(str(r[5] or "").strip())
                    level = str(r[6] or "abc").strip()
                    folder = str(r[7] or sheet_name).strip()
                    ex_zh = str(r[8] or "").strip() if len(r) > 8 else ""
                    ex_py = _auto_pinyin(ex_zh)
                    ex_vi = ""
                else:
                    word = str(r[0] or "").strip()
                    pinyin = str(r[1] or "").strip() if len(r) > 1 and r[1] else _auto_pinyin(word)
                    hanviet = str(r[2] or "").strip() if len(r) > 2 and r[2] else ""
                    meaning = clean_meaning_text(str(r[3] or "").strip() if len(r) > 3 and r[3] else "")
                    ex_zh = str(r[4] or "").strip() if len(r) > 4 and r[4] else ""
                    ex_py = str(r[5] or "").strip() if len(r) > 5 and r[5] else _auto_pinyin(ex_zh)
                    ex_vi = str(r[6] or "").strip() if len(r) > 6 and r[6] else ""
                    level = str(r[7] or "abc").strip() if len(r) > 7 and r[7] else "abc"
                    folder_col = str(r[8] or "").strip() if len(r) > 8 and r[8] else ""

                    # Nếu chọn lấy theo tên Sheet hoặc cột Folder trống / bị ghi nhầm chữ "abc"
                    if use_sheet_name_as_folder or not folder_col or folder_col.lower() == "abc":
                        folder = sheet_name.strip()
                    else:
                        folder = folder_col
                    pos = "Từ vựng"

                if not word or word.lower() == "word":
                    continue

                full_ex = f"{ex_zh}\n{ex_py}\n{ex_vi}".strip() if ex_zh else ""
                cursor.execute("INSERT OR IGNORE INTO custom_topics (topic_name) VALUES (?)", (folder,))
                cursor.execute("""
                    INSERT INTO saved_vocabulary (
                        word, pinyin, hanviet, pos, meaning, zh_meaning, hsk,
                        examples, example_zh, example_pinyin, example_vi, topic, notes
                    )
                    VALUES (?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?, ?, '')
                    ON CONFLICT(word) DO UPDATE SET
                        pinyin=excluded.pinyin,
                        hanviet=excluded.hanviet,
                        meaning=excluded.meaning,
                        hsk=excluded.hsk,
                        examples=excluded.examples,
                        example_zh=excluded.example_zh,
                        example_pinyin=excluded.example_pinyin,
                        example_vi=excluded.example_vi,
                        topic=excluded.topic
                """, (word, pinyin, hanviet, pos, meaning, level, full_ex, ex_zh, ex_py, ex_vi, folder))

                added_folders.add(folder)
                imported_count += 1

        conn.commit()
    finally:
        conn.close()

    return imported_count, sorted(list(added_folders))


def backup_database(destination_path):
    shutil.copy2(DB_NAME, destination_path)