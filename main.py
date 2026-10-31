import math
import random
import time
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import threading

from config import Config
import database
import ai_service
from vocab_farm_engine import VocabFarmEngine

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def enable_button_wrap(btn: ctk.CTkButton, wraplength: int = 500, justify: str = "left"):
    """
    Hàm khắc phục triệt để lỗi mất chữ / cắt chữ trên CTkButton khi câu tiếng Trung hoặc tiếng Việt dài.
    """
    try:
        if hasattr(btn, "_text_label") and btn._text_label is not None:
            btn._text_label.configure(wraplength=wraplength, justify=justify)
    except Exception:
        pass


class TranslatorProApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        database.init_db()
        self.farm_engine = VocabFarmEngine()

        self.title(f"{Config.APP_NAME} - {Config.APP_SUBTITLE}")
        self.geometry("1340x860")
        self.minsize(1140, 740)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.current_vocab_data = None
        self.current_grammar_data = None
        self.selected_saved_word_id = None
        self.selected_farm_plot_id = "0"

        self.saved_page_index = 1
        self.saved_page_size = 20
        self.saved_total_pages = 1

        self._create_sidebar()
        self._create_pages()
        self.select_page("translate")
        self._start_farm_background_ticker()

    # =========================================================================
    # ĐỒNG BỘ DANH SÁCH CHỦ ĐỀ / FOLDER
    # =========================================================================
    def _sync_topic_menus(self, selected_topic: str = None):
        topics = database.get_all_topics()
        all_with_topics = ["Tất cả"] + topics

        if hasattr(self, "vocab_topic_menu"):
            cur_v = selected_topic if (selected_topic and selected_topic in topics) else self.vocab_topic_menu.get()
            self.vocab_topic_menu.configure(values=topics)
            self.vocab_topic_menu.set(cur_v if cur_v in topics else topics[0])

        if hasattr(self, "filter_topic_menu"):
            cur = selected_topic if (selected_topic and selected_topic in all_with_topics) else self.filter_topic_menu.get()
            self.filter_topic_menu.configure(values=all_with_topics)
            self.filter_topic_menu.set(cur if cur in all_with_topics else "Tất cả")

        if hasattr(self, "edit_topic_menu"):
            cur_e = selected_topic if (selected_topic and selected_topic in topics) else self.edit_topic_menu.get()
            self.edit_topic_menu.configure(values=topics)
            self.edit_topic_menu.set(cur_e if cur_e in topics else topics[0])

        if hasattr(self, "farm_topic_menu"):
            cur_f = self.farm_topic_menu.get()
            self.farm_topic_menu.configure(values=all_with_topics)
            if selected_topic and selected_topic in all_with_topics:
                self.farm_topic_menu.set(selected_topic)
            elif cur_f not in all_with_topics:
                self.farm_topic_menu.set(topics[0] if topics else "Tất cả")

    def _prompt_add_topic(self):
        dlg = ctk.CTkInputDialog(
            text="Nhập tên Chủ đề / Folder mới (VD: Camvision, Bài 41-50, Vision Master...):",
            title="➕ Thêm Chủ đề / Folder mới"
        )
        new_topic = dlg.get_input()
        if new_topic and new_topic.strip():
            t_name = new_topic.strip()
            database.add_custom_topic(t_name)
            self._sync_topic_menus(selected_topic=t_name)
            messagebox.showinfo("Thành công", f"Đã thêm Folder mới: [{t_name}]!")

    def _prompt_delete_current_topic(self):
        cur_topic = self.filter_topic_menu.get()
        if cur_topic == "Tất cả":
            messagebox.showwarning("Thông báo", "Hãy chọn một Folder cụ thể ở ô lọc 'Folder / Chủ đề' để xóa!")
            return
        delete_words = messagebox.askyesnocancel(
            "Xác nhận xóa Folder",
            f"Bạn đang chọn xóa Folder [{cur_topic}].\n\n"
            f"• Bấm YES: Xóa Folder [{cur_topic}] VÀ xóa luôn các từ vựng bên trong nó.\n"
            f"• Bấm NO: Chỉ xóa tên Folder [{cur_topic}] (chuyển từ vựng sang Camvision).\n"
            f"• Bấm CANCEL: Hủy bỏ."
        )
        if delete_words is None:
            return
        database.delete_custom_topic(cur_topic, delete_words_inside=bool(delete_words))
        self.saved_page_index = 1
        self._sync_topic_menus(selected_topic="Tất cả")
        self._refresh_saved_words()

    # =========================================================================
    # THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR)
    # =========================================================================
    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=245, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(9, weight=1)

        title_lbl = ctk.CTkLabel(
            self.sidebar,
            text="中越智能翻译助手\nTRANSLATOR PRO",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        )
        title_lbl.grid(row=0, column=0, padx=20, pady=(22, 4))

        sub_lbl = ctk.CTkLabel(
            self.sidebar,
            text="Dịch thuật • Học từ • Linh Điền Ký",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "gray70")
        )
        sub_lbl.grid(row=1, column=0, padx=20, pady=(0, 16))

        self.nav_buttons = {}
        nav_items = [
            ("translate", "1. Dịch thuật (翻译)"),
            ("vocab", "2. Tra cứu từ vựng (词典)"),
            ("grammar", "3. Phân tích ngữ pháp (语法)"),
            ("history", "4. Lịch sử dịch (历史)"),
            ("saved", "5. Sổ từ & Flashcard (生词本)"),
            ("farm", "6. Linh Điền Ký (灵田记)"),
            ("settings", "7. Cài đặt (设置)")
        ]

        for idx, (key, label) in enumerate(nav_items, start=2):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=40,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=lambda k=key: self.select_page(k)
            )
            btn.grid(row=idx, column=0, padx=14, pady=5, sticky="ew")
            self.nav_buttons[key] = btn

        self.status_lbl = ctk.CTkLabel(
            self.sidebar,
            text=f"Model: {Config.GEMINI_MODEL}",
            font=ctk.CTkFont(size=12),
            text_color=("gray25", "gray75")
        )
        self.status_lbl.grid(row=10, column=0, padx=16, pady=(10, 18), sticky="s")

    def _create_pages(self):
        self.pages = {
            "translate": ctk.CTkFrame(self, corner_radius=0, fg_color="transparent"),
            "vocab": ctk.CTkFrame(self, corner_radius=0, fg_color="transparent"),
            "grammar": ctk.CTkFrame(self, corner_radius=0, fg_color="transparent"),
            "history": ctk.CTkFrame(self, corner_radius=0, fg_color="transparent"),
            "saved": ctk.CTkFrame(self, corner_radius=0, fg_color="transparent"),
            "farm": ctk.CTkFrame(self, corner_radius=0, fg_color="transparent"),
            "settings": ctk.CTkFrame(self, corner_radius=0, fg_color="transparent"),
        }

        self._build_translate_page()
        self._build_vocab_page()
        self._build_grammar_page()
        self._build_history_page()
        self._build_saved_words_page()
        self._build_farm_page()
        self._build_settings_page()
        self._sync_topic_menus()

    def select_page(self, page_key: str):
        for k, btn in self.nav_buttons.items():
            if k == page_key:
                btn.configure(fg_color=("#1F538D", "#14375E"))
            else:
                btn.configure(fg_color=("#3B8ED0", "#1F6AA5"))

        for k, frame in self.pages.items():
            if k == page_key:
                frame.grid(row=0, column=1, sticky="nsew", padx=16, pady=12)
            else:
                frame.grid_forget()

        self._sync_topic_menus()
        if page_key == "history":
            self._refresh_history()
        elif page_key == "saved":
            self._refresh_saved_words()
        elif page_key == "grammar":
            self._refresh_saved_grammar()
        elif page_key == "farm":
            self._sync_farm_vocab_pool_from_selected_folder()
            self._refresh_farm_ui()

    def _sync_farm_vocab_pool_from_selected_folder(self):
        """Đảm bảo Game Engine luôn dùng đúng vocab_pool của Folder người chơi đang chọn."""
        topic = self.farm_topic_menu.get() if hasattr(self, "farm_topic_menu") else "Camvision"
        pool = self._get_vocab_pool_for_learning(topic_filter=topic)
        self.farm_engine.sync_vocab_pool(topic, pool)

    # =========================================================================
    # TRANG 1: DỊCH THUẬT AI
    # =========================================================================
    def _build_translate_page(self):
        page = self.pages["translate"]
        page.grid_columnconfigure((0, 1), weight=1)
        page.grid_rowconfigure(2, weight=3)
        page.grid_rowconfigure(4, weight=2)

        top_bar = ctk.CTkFrame(page)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(top_bar, text="Chiều dịch:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(12, 4), pady=10)
        self.dir_menu = ctk.CTkOptionMenu(
            top_bar,
            width=190,
            values=["Tự động nhận diện", "Tiếng Trung → Tiếng Việt", "Tiếng Việt → Tiếng Trung"]
        )
        self.dir_menu.pack(side="left", padx=4, pady=10)

        self.btn_swap = ctk.CTkButton(top_bar, text="⇄ Đảo chiều", width=100, command=self._swap_translation_direction)
        self.btn_swap.pack(side="left", padx=6, pady=10)

        ctk.CTkLabel(top_bar, text="Chế độ:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(12, 4), pady=10)
        self.mode_menu = ctk.CTkOptionMenu(top_bar, width=210, values=Config.TRANSLATION_MODES)
        self.mode_menu.pack(side="left", padx=4, pady=10)

        self.btn_translate = ctk.CTkButton(
            top_bar,
            text="Dịch ngay (翻译)",
            width=140,
            fg_color="#0D7A5F",
            hover_color="#095945",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_translation
        )
        self.btn_translate.pack(side="right", padx=12, pady=10)

        self.lbl_source_info = ctk.CTkLabel(page, text="Văn bản gốc (Nhập từ, câu hoặc đoạn văn tài liệu):", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_source_info.grid(row=1, column=0, sticky="w", padx=4, pady=(0, 4))

        self.lbl_target_info = ctk.CTkLabel(page, text="Kết quả dịch:", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_target_info.grid(row=1, column=1, sticky="w", padx=8, pady=(0, 4))

        self.txt_source = ctk.CTkTextbox(page, font=("Microsoft YaHei UI", 15), wrap="word")
        self.txt_source.grid(row=2, column=0, sticky="nsew", padx=(0, 6), pady=4)

        self.txt_target = ctk.CTkTextbox(page, font=("Microsoft YaHei UI", 15), wrap="word")
        self.txt_target.grid(row=2, column=1, sticky="nsew", padx=(6, 0), pady=4)

        action_bar = ctk.CTkFrame(page, fg_color="transparent")
        action_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=6)

        ctk.CTkButton(action_bar, text="Xóa nội dung", width=110, fg_color="#6C757D", hover_color="#5A6268", command=self._clear_translation).pack(side="left", padx=(0, 6))
        ctk.CTkButton(action_bar, text="Dịch lại", width=95, command=self._start_translation).pack(side="left", padx=6)
        ctk.CTkButton(action_bar, text="Sao chép kết quả", width=130, command=self._copy_translation_result).pack(side="left", padx=6)

        self.btn_back_trans = ctk.CTkButton(
            action_bar,
            text="Kiểm tra dịch ngược (反向验证)",
            width=200,
            fg_color="#D97706",
            hover_color="#B45309",
            command=self._start_back_translation
        )
        self.btn_back_trans.pack(side="left", padx=6)

        ctk.CTkButton(action_bar, text="Lưu vào lịch sử", width=120, command=self._manual_save_history).pack(side="right", padx=6)
        ctk.CTkButton(action_bar, text="+ Thêm vào sổ từ vựng", width=160, command=self._quick_send_to_vocab).pack(side="right", padx=6)

        self.txt_trans_extra = ctk.CTkTextbox(page, font=("Microsoft YaHei UI", 13), wrap="word")
        self.txt_trans_extra.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(4, 0))
        self.txt_trans_extra.insert("1.0", "Ghi chú Pinyin, giải thích thuật ngữ chuyên ngành và kết quả Kiểm tra dịch ngược sẽ hiển thị tại đây...")

    def _swap_translation_direction(self):
        current_dir = self.dir_menu.get()
        if current_dir == "Tiếng Trung → Tiếng Việt":
            self.dir_menu.set("Tiếng Việt → Tiếng Trung")
        elif current_dir == "Tiếng Việt → Tiếng Trung":
            self.dir_menu.set("Tiếng Trung → Tiếng Việt")

        src_text = self.txt_source.get("1.0", tk.END).strip()
        tgt_text = self.txt_target.get("1.0", tk.END).strip()
        if tgt_text:
            self.txt_source.delete("1.0", tk.END)
            self.txt_source.insert("1.0", tgt_text)
            self.txt_target.delete("1.0", tk.END)
            self.txt_target.insert("1.0", src_text)

    def _clear_translation(self):
        self.txt_source.delete("1.0", tk.END)
        self.txt_target.delete("1.0", tk.END)
        self.txt_trans_extra.delete("1.0", tk.END)

    def _copy_translation_result(self):
        res = self.txt_target.get("1.0", tk.END).strip()
        if not res:
            messagebox.showwarning("Thông báo", "Chưa có kết quả dịch để sao chép!")
            return
        self.clipboard_clear()
        self.clipboard_append(res)
        messagebox.showinfo("Đã sao chép", "Đã sao chép văn bản dịch vào Clipboard!")

    def _manual_save_history(self):
        src = self.txt_source.get("1.0", tk.END).strip()
        tgt = self.txt_target.get("1.0", tk.END).strip()
        if not src or not tgt:
            messagebox.showwarning("Thông báo", "Cần có cả văn bản gốc và kết quả dịch để lưu lịch sử!")
            return
        database.save_translation(src, tgt, "", "", self.dir_menu.get(), self.mode_menu.get())
        messagebox.showinfo("Thành công", "Đã lưu bản dịch vào lịch sử!")

    def _quick_send_to_vocab(self):
        src = self.txt_source.get("1.0", tk.END).strip()
        if not src:
            messagebox.showwarning("Thông báo", "Hãy nhập từ hoặc cụm từ vào ô Văn bản gốc trước!")
            return
        self.select_page("vocab")
        self.entry_vocab.delete(0, tk.END)
        self.entry_vocab.insert(0, src)
        self._start_vocab_lookup()

    def _start_translation(self):
        src_text = self.txt_source.get("1.0", tk.END).strip()
        if not src_text:
            messagebox.showwarning("Chưa nhập nội dung", "Vui lòng nhập văn bản cần dịch!")
            return

        direction = self.dir_menu.get()
        mode = self.mode_menu.get()
        self.btn_translate.configure(state="disabled", text="Đang dịch...")
        self.txt_trans_extra.delete("1.0", tk.END)
        self.txt_trans_extra.insert("1.0", "⏳ Đang phân tích ngữ cảnh và dịch thuật...")

        def worker():
            try:
                res = ai_service.request_translation(src_text, direction, mode)
                self.after(0, lambda r=res: self._on_translation_success(src_text, direction, mode, r))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda m=err_msg: messagebox.showerror("Lỗi dịch thuật", m))
            finally:
                self.after(0, lambda: self.btn_translate.configure(state="normal", text="Dịch ngay (翻译)"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_translation_success(self, src_text, direction, mode, res: dict):
        translation = res.get("translation", "")
        src_lang = res.get("detected_lang", "")
        tgt_lang = res.get("target_lang", "")

        self.lbl_source_info.configure(text=f"Văn bản gốc (Ngôn ngữ nguồn: {src_lang}):")
        self.lbl_target_info.configure(text=f"Kết quả dịch (Ngôn ngữ đích: {tgt_lang} | Chế độ: {mode}):")

        self.txt_target.delete("1.0", tk.END)
        self.txt_target.insert("1.0", translation)

        extra_lines = []
        if res.get("pinyin"):
            extra_lines.append(f"📌 Pinyin: {res['pinyin']}")
        if res.get("alternative"):
            extra_lines.append(f"🔄 Thông tin bổ sung: {res['alternative']}")
        if res.get("key_terms"):
            extra_lines.append(f"🛠️ Thuật ngữ & Từ vựng quan trọng:\n{res['key_terms']}")

        self.txt_trans_extra.delete("1.0", tk.END)
        self.txt_trans_extra.insert("1.0", "\n\n".join(extra_lines) if extra_lines else "Hoàn tất dịch thuật.")
        database.save_translation(src_text, translation, src_lang, tgt_lang, direction, mode)

    def _start_back_translation(self):
        src_text = self.txt_source.get("1.0", tk.END).strip()
        tgt_text = self.txt_target.get("1.0", tk.END).strip()
        if not src_text or not tgt_text:
            messagebox.showwarning("Thông báo", "Vui lòng thực hiện dịch văn bản trước khi kiểm tra dịch ngược!")
            return

        mode = self.mode_menu.get()
        self.btn_back_trans.configure(state="disabled", text="Đang kiểm tra...")

        def worker():
            try:
                res = ai_service.request_back_translation(src_text, tgt_text, mode)
                self.after(0, lambda r=res: self._on_back_translation_success(r))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda m=err_msg: messagebox.showerror("Lỗi dịch ngược", m))
            finally:
                self.after(0, lambda: self.btn_back_trans.configure(state="normal", text="Kiểm tra dịch ngược (反向验证)"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_back_translation_success(self, res: dict):
        report = (
            "\n\n" + "=" * 65 + "\n"
            "🔍 KẾT QUẢ KIỂM TRA BẢN DỊCH NGƯỢC (BACK-TRANSLATION)\n"
            f"• Bản dịch ngược về ngôn ngữ gốc: {res.get('back_translation', '')}\n"
            f"• Đánh giá độ chuẩn xác: {res.get('accuracy_score', '')}\n"
            f"• Kiểm tra thiếu/thừa thông tin: {res.get('missing_or_added', '')}\n"
            f"• Nhận xét đối chiếu: {res.get('comparison_notes', '')}\n"
            + "=" * 65
        )
        self.txt_trans_extra.insert(tk.END, report)
        self.txt_trans_extra.see(tk.END)

    # =========================================================================
    # TRANG 2: TRA CỨU TỪ VỰNG TRỰC QUAN
    # =========================================================================
    def _build_vocab_page(self):
        page = self.pages["vocab"]
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)

        top_bar = ctk.CTkFrame(page)
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.entry_vocab = ctk.CTkEntry(
            top_bar,
            placeholder_text="Nhập từ vựng cần tra cứu (VD: 适应, 测试运行, 机器视觉, 任何)...",
            font=("Microsoft YaHei UI", 14),
            height=38
        )
        self.entry_vocab.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.entry_vocab.bind("<Return>", lambda e: self._start_vocab_lookup())

        self.btn_vocab_search = ctk.CTkButton(top_bar, text="Tra cứu (查询)", width=130, height=38, command=self._start_vocab_lookup)
        self.btn_vocab_search.pack(side="left", padx=6, pady=10)

        ctk.CTkButton(top_bar, text="Sao chép", width=105, height=38, command=self._copy_vocab_result).pack(side="left", padx=6, pady=10)

        save_bar = ctk.CTkFrame(page)
        save_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(save_bar, text="Folder lưu trữ:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(12, 4), pady=8)
        self.vocab_topic_menu = ctk.CTkOptionMenu(save_bar, values=database.get_all_topics(), width=170)
        self.vocab_topic_menu.pack(side="left", padx=4, pady=8)

        ctk.CTkButton(save_bar, text="+ Thêm Folder", width=110, fg_color="#1F538D", command=self._prompt_add_topic).pack(side="left", padx=4, pady=8)

        ctk.CTkLabel(save_bar, text="Ghi chú:").pack(side="left", padx=(10, 4), pady=8)
        self.entry_vocab_note = ctk.CTkEntry(save_bar, placeholder_text="Ghi chú thêm (tùy chọn)...", width=220)
        self.entry_vocab_note.pack(side="left", fill="x", expand=True, padx=4, pady=8)

        self.btn_save_vocab = ctk.CTkButton(
            save_bar,
            text="⭐ Lưu vào Sổ từ vựng",
            state="disabled",
            fg_color="#0D7A5F",
            hover_color="#095945",
            command=self._save_current_vocab
        )
        self.btn_save_vocab.pack(side="right", padx=12, pady=8)

        self.txt_vocab_result = ctk.CTkTextbox(page, font=("Microsoft YaHei UI", 15), wrap="word")
        self.txt_vocab_result.grid(row=2, column=0, sticky="nsew")

    def _start_vocab_lookup(self):
        query = self.entry_vocab.get().strip()
        if not query:
            messagebox.showwarning("Thông báo", "Vui lòng nhập từ vựng cần tra cứu!")
            return

        self.btn_vocab_search.configure(state="disabled", text="Đang tra cứu...")
        self.txt_vocab_result.delete("1.0", tk.END)
        self.txt_vocab_result.insert("1.0", f"⏳ Đang phân tích từ vựng '{query}'...")

        def worker():
            try:
                data = ai_service.lookup_vocabulary(query)
                self.after(0, lambda d=data: self._display_vocab_data(d))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda m=err_msg: messagebox.showerror("Lỗi tra cứu", m))
            finally:
                self.after(0, lambda: self.btn_vocab_search.configure(state="normal", text="Tra cứu (查询)"))

        threading.Thread(target=worker, daemon=True).start()

    def _display_vocab_data(self, d: dict):
        self.current_vocab_data = d
        self.btn_save_vocab.configure(state="normal")

        rec_topic = d.get("recommended_topic", "")
        if rec_topic and rec_topic in database.get_all_topics():
            self.vocab_topic_menu.set(rec_topic)

        lines = [
            f"📖 {d.get('word', '')}",
            f"Pinyin: {d.get('pinyin', '')}",
            f"Âm Hán Việt: {d.get('hanviet', '').upper()}",
            f"Từ loại: {d.get('pos', 'Từ vựng')}",
            f"HSK: {d.get('hsk', 'Khoảng HSK4')}",
            f"Nghĩa: {d.get('meaning_common', '')}",
            f"\n👉 {d.get('usage', '')}",
            "\n" + "─" * 68,
            "🌱 1. Ví dụ dễ\n"
        ]

        for idx, ex in enumerate(d.get("examples", [])[:3], start=1):
            lines.append(f"{idx}. {ex.get('zh', '')}")
            lines.append(f"   {ex.get('pinyin', '')}")
            lines.append(f"   {ex.get('vi', '')}\n")

        collocations = d.get("collocations", [])
        if collocations:
            lines.append("─" * 68)
            lines.append("🔥 2. Cụm từ thường gặp\n")
            lines.append(f"{'Tiếng Trung':<16} {'Pinyin':<24} {'Nghĩa'}")
            lines.append("-" * 68)
            for zh_c, py_c, vi_c in collocations:
                lines.append(f"{zh_c:<16} {py_c:<24} {vi_c}")
            lines.append("")

        if d.get("grammar_note"):
            lines.append("─" * 68)
            lines.append("🧠 3. Cấu trúc ngữ pháp\n")
            lines.append(d.get("grammar_note", "") + "\n")

        dialogue = d.get("dialogue", [])
        if dialogue:
            lines.append("─" * 68)
            lines.append("💬 4. Hội thoại thực tế\n")
            for zh_d, py_d, vi_d in dialogue:
                lines.append(zh_d)
                lines.append(py_d)
                lines.append(vi_d + "\n")

        self.txt_vocab_result.delete("1.0", tk.END)
        self.txt_vocab_result.insert("1.0", "\n".join(lines))

    def _copy_vocab_result(self):
        content = self.txt_vocab_result.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Thành công", "Đã sao chép nội dung từ vựng!")

    def _save_current_vocab(self):
        if not self.current_vocab_data:
            return
        d = self.current_vocab_data
        clean_meaning = database.clean_meaning_text(d.get("meaning_common", ""))

        examples = d.get("examples", [])
        ex1 = examples[0] if examples else {}
        topic_chosen = self.vocab_topic_menu.get()

        database.save_word(
            word=d.get("word", ""),
            pinyin=d.get("pinyin", ""),
            hanviet=d.get("hanviet", ""),
            pos=d.get("pos", "Từ vựng"),
            meaning=clean_meaning,
            hsk="abc",
            topic=topic_chosen,
            notes=self.entry_vocab_note.get().strip(),
            example_zh=ex1.get("zh", ""),
            example_pinyin=ex1.get("pinyin", ""),
            example_vi=ex1.get("vi", "")
        )
        self._sync_topic_menus()
        messagebox.showinfo("Đã lưu", f"Đã lưu từ '{d.get('word')}' vào Folder [{topic_chosen}]!")

    # =========================================================================
    # TRANG 3: PHÂN TÍCH NGỮ PHÁP
    # =========================================================================
    def _build_grammar_page(self):
        page = self.pages["grammar"]
        page.grid_columnconfigure(0, weight=3)
        page.grid_columnconfigure(1, weight=2)
        page.grid_rowconfigure(2, weight=1)

        lbl = ctk.CTkLabel(page, text="Nhập câu tiếng Trung cần phân tích cấu trúc ngữ pháp:", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        top_box = ctk.CTkFrame(page)
        top_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        top_box.grid_columnconfigure(0, weight=1)

        self.txt_grammar_input = ctk.CTkTextbox(top_box, height=75, font=("Microsoft YaHei UI", 15), wrap="word")
        self.txt_grammar_input.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        btn_col = ctk.CTkFrame(top_box, fg_color="transparent")
        btn_col.grid(row=0, column=1, padx=(0, 10), pady=8)

        self.btn_grammar_run = ctk.CTkButton(
            btn_col,
            text="Phân tích ngữ pháp (语法分析)",
            width=190,
            height=36,
            font=ctk.CTkFont(weight="bold"),
            command=self._start_grammar_analysis
        )
        self.btn_grammar_run.pack(pady=(0, 6))

        self.btn_grammar_save = ctk.CTkButton(
            btn_col,
            text="⭐ Lưu câu đang phân tích",
            width=190,
            height=32,
            fg_color="#0D7A5F",
            hover_color="#095945",
            command=self._manual_save_grammar
        )
        self.btn_grammar_save.pack()

        self.txt_grammar_output = ctk.CTkTextbox(page, font=("Microsoft YaHei UI", 14), wrap="word")
        self.txt_grammar_output.grid(row=2, column=0, sticky="nsew", padx=(0, 8))

        saved_grammar_frame = ctk.CTkFrame(page)
        saved_grammar_frame.grid(row=2, column=1, sticky="nsew", padx=(8, 0))
        saved_grammar_frame.grid_columnconfigure(0, weight=1)
        saved_grammar_frame.grid_rowconfigure(2, weight=1)

        header_row = ctk.CTkFrame(saved_grammar_frame, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))

        ctk.CTkLabel(header_row, text="📚 Các câu ngữ pháp đã lưu", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        ctk.CTkButton(
            header_row,
            text="🗑️ Xóa tất cả",
            width=100,
            height=28,
            fg_color="#C0392B",
            hover_color="#962D22",
            command=self._clear_all_saved_grammar
        ).pack(side="right")

        search_row = ctk.CTkFrame(saved_grammar_frame, fg_color="transparent")
        search_row.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        search_row.grid_columnconfigure(0, weight=1)

        self.entry_grammar_search = ctk.CTkEntry(search_row, placeholder_text="Tìm câu đã lưu...")
        self.entry_grammar_search.grid(row=0, column=0, sticky="ew", padx=(4, 4))
        self.entry_grammar_search.bind("<Return>", lambda e: self._refresh_saved_grammar())

        ctk.CTkButton(search_row, text="Tìm", width=60, command=self._refresh_saved_grammar).grid(row=0, column=1, padx=4)

        self.scroll_grammar_saved = ctk.CTkScrollableFrame(saved_grammar_frame)
        self.scroll_grammar_saved.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.scroll_grammar_saved.grid_columnconfigure(0, weight=1)

    def _start_grammar_analysis(self):
        sentence = self.txt_grammar_input.get("1.0", tk.END).strip()
        if not sentence:
            messagebox.showwarning("Thông báo", "Vui lòng nhập câu tiếng Trung cần phân tích!")
            return

        self.btn_grammar_run.configure(state="disabled", text="Đang phân tích...")
        self.txt_grammar_output.delete("1.0", tk.END)
        self.txt_grammar_output.insert("1.0", "⏳ Đang phân tích cấu trúc câu...")

        def worker():
            try:
                res_dict = ai_service.analyze_grammar(sentence)
                self.after(0, lambda r=res_dict: self._display_grammar_result(r))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda m=err_msg: messagebox.showerror("Lỗi phân tích", m))
            finally:
                self.after(0, lambda: self.btn_grammar_run.configure(state="normal", text="Phân tích ngữ pháp (语法分析)"))

        threading.Thread(target=worker, daemon=True).start()

    def _display_grammar_result(self, res_dict: dict):
        self.current_grammar_data = res_dict
        self.txt_grammar_output.delete("1.0", tk.END)
        self.txt_grammar_output.insert("1.0", res_dict.get("report", ""))

        database.save_grammar_sentence(
            sentence=res_dict.get("sentence", ""),
            pinyin=res_dict.get("pinyin", ""),
            meaning=res_dict.get("meaning", ""),
            analysis_result=res_dict.get("report", "")
        )
        self._refresh_saved_grammar()

    def _manual_save_grammar(self):
        if not self.current_grammar_data:
            messagebox.showwarning("Thông báo", "Hãy bấm 'Phân tích ngữ pháp' một câu trước khi lưu!")
            return
        r = self.current_grammar_data
        database.save_grammar_sentence(
            sentence=r.get("sentence", ""),
            pinyin=r.get("pinyin", ""),
            meaning=r.get("meaning", ""),
            analysis_result=r.get("report", "")
        )
        self._refresh_saved_grammar()
        messagebox.showinfo("Thành công", f"Đã lưu câu '{r.get('sentence')}'!")

    def _refresh_saved_grammar(self):
        for w in self.scroll_grammar_saved.winfo_children():
            w.destroy()

        q = self.entry_grammar_search.get().strip()
        rows = database.get_saved_grammar(search_query=q, limit=60)

        if not rows:
            ctk.CTkLabel(self.scroll_grammar_saved, text="Chưa có câu ngữ pháp nào được lưu.", font=ctk.CTkFont(size=13)).pack(pady=20)
            return

        for row in rows:
            g_id, sent, py, meaning, report, created_at = row
            card = ctk.CTkFrame(self.scroll_grammar_saved)
            card.pack(fill="x", padx=4, pady=4)
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(card, text=sent, font=("Microsoft YaHei UI", 14, "bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=(6, 0))
            ctk.CTkLabel(card, text=f"{py}\n→ {meaning}", font=("Microsoft YaHei UI", 12), justify="left", anchor="w", wraplength=260, text_color=("gray25", "gray75")).grid(row=1, column=0, sticky="w", padx=10, pady=(2, 6))

            btn_col = ctk.CTkFrame(card, fg_color="transparent")
            btn_col.grid(row=0, column=1, rowspan=2, padx=6, pady=4)

            ctk.CTkButton(btn_col, text="Xem lại", width=68, height=26, command=lambda s=sent, rep=report: self._load_saved_grammar_item(s, rep)).pack(pady=2)
            ctk.CTkButton(btn_col, text="Xóa", width=68, height=26, fg_color="#C0392B", hover_color="#962D22", command=lambda i=g_id: self._delete_saved_grammar_item(i)).pack(pady=2)

    def _load_saved_grammar_item(self, sentence: str, report: str):
        self.txt_grammar_input.delete("1.0", tk.END)
        self.txt_grammar_input.insert("1.0", sentence)
        self.txt_grammar_output.delete("1.0", tk.END)
        self.txt_grammar_output.insert("1.0", report)

    def _delete_saved_grammar_item(self, item_id: int):
        database.delete_grammar_item(item_id)
        self._refresh_saved_grammar()

    def _clear_all_saved_grammar(self):
        if messagebox.askyesno("Xác nhận xóa tất cả", "Bạn có chắc chắn muốn xóa toàn bộ các câu ngữ pháp đã lưu không?"):
            database.clear_all_grammar()
            self._refresh_saved_grammar()

    # =========================================================================
    # TRANG 4: LỊCH SỬ DỊCH THUẬT
    # =========================================================================
    def _build_history_page(self):
        page = self.pages["history"]
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(page)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.entry_hist_search = ctk.CTkEntry(bar, placeholder_text="Tìm kiếm nội dung trong lịch sử dịch...", width=350)
        self.entry_hist_search.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self.entry_hist_search.bind("<Return>", lambda e: self._refresh_history())

        ctk.CTkButton(bar, text="Tìm kiếm", width=100, command=self._refresh_history).pack(side="left", padx=5, pady=10)
        ctk.CTkButton(bar, text="Làm mới", width=90, command=lambda: [self.entry_hist_search.delete(0, tk.END), self._refresh_history()]).pack(side="left", padx=5, pady=10)
        ctk.CTkButton(bar, text="🗑️ Xóa tất cả lịch sử", width=160, fg_color="#C0392B", hover_color="#962D22", command=self._clear_all_history).pack(side="right", padx=10, pady=10)

        self.scroll_history = ctk.CTkScrollableFrame(page)
        self.scroll_history.grid(row=1, column=0, sticky="nsew")
        self.scroll_history.grid_columnconfigure(0, weight=1)

    def _refresh_history(self):
        for widget in self.scroll_history.winfo_children():
            widget.destroy()

        query = self.entry_hist_search.get().strip()
        rows = database.get_history(search_query=query, limit=60)

        if not rows:
            ctk.CTkLabel(self.scroll_history, text="Chưa có dữ liệu lịch sử dịch.", font=ctk.CTkFont(size=14)).pack(pady=30)
            return

        for r in rows:
            item_id, src, tgt, src_lang, tgt_lang, mode, created_at = r
            card = ctk.CTkFrame(self.scroll_history)
            card.pack(fill="x", padx=6, pady=5)
            card.grid_columnconfigure(0, weight=1)

            header_text = f"#{item_id} | 🕒 {created_at} | Chế độ: {mode}"
            ctk.CTkLabel(card, text=header_text, font=ctk.CTkFont(size=12, weight="bold"), text_color=("gray30", "gray70")).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 2))

            body_text = f"Gốc: {src}\nDịch: {tgt}"
            ctk.CTkLabel(card, text=body_text, font=("Microsoft YaHei UI", 13), justify="left", anchor="w", wraplength=780).grid(row=1, column=0, sticky="w", padx=12, pady=(2, 8))

            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=8)

            ctk.CTkButton(btn_frame, text="Xem lại", width=80, height=28, command=lambda s=src, t=tgt: self._reuse_history_item(s, t)).pack(pady=2)
            ctk.CTkButton(btn_frame, text="Xóa", width=80, height=28, fg_color="#C0392B", hover_color="#962D22", command=lambda i=item_id: self._delete_single_history(i)).pack(pady=2)

    def _reuse_history_item(self, src: str, tgt: str):
        self.select_page("translate")
        self.txt_source.delete("1.0", tk.END)
        self.txt_source.insert("1.0", src)
        self.txt_target.delete("1.0", tk.END)
        self.txt_target.insert("1.0", tgt)

    def _delete_single_history(self, item_id: int):
        database.delete_history_item(item_id)
        self._refresh_history()

    def _clear_all_history(self):
        if messagebox.askyesno("Xác nhận xóa", "Bạn có chắc chắn muốn xóa toàn bộ lịch sử dịch không?"):
            database.clear_all_history()
            self._refresh_history()

    # =========================================================================
    # TRANG 5: SỔ TỪ VỰNG PHÂN TRANG TỐC ĐỘ CAO
    # =========================================================================
    def _build_saved_words_page(self):
        page = self.pages["saved"]
        page.grid_columnconfigure(0, weight=3)
        page.grid_columnconfigure(1, weight=2)
        page.grid_rowconfigure(2, weight=1)

        top_bar1 = ctk.CTkFrame(page)
        top_bar1.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        self.entry_saved_search = ctk.CTkEntry(top_bar1, placeholder_text="Tìm Word, Pinyin, Sino-Vietnamese, Meaning...", width=220)
        self.entry_saved_search.pack(side="left", padx=10, pady=8, fill="x", expand=True)
        self.entry_saved_search.bind("<Return>", lambda e: self._on_search_or_filter_saved())

        ctk.CTkLabel(top_bar1, text="Folder / Chủ đề:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(6, 4))
        self.filter_topic_menu = ctk.CTkOptionMenu(
            top_bar1,
            values=["Tất cả"] + database.get_all_topics(),
            width=165,
            command=lambda _: self._on_search_or_filter_saved()
        )
        self.filter_topic_menu.set("Camvision")
        self.filter_topic_menu.pack(side="left", padx=4, pady=8)

        ctk.CTkButton(top_bar1, text="Tìm / Lọc", width=80, command=self._on_search_or_filter_saved).pack(side="left", padx=4, pady=8)
        ctk.CTkButton(top_bar1, text="➕ Thêm Folder", width=115, fg_color="#1F538D", command=self._prompt_add_topic).pack(side="left", padx=4, pady=8)
        ctk.CTkButton(top_bar1, text="🗑️ Xóa Folder", width=110, fg_color="#C0392B", hover_color="#962D22", command=self._prompt_delete_current_topic).pack(side="left", padx=(4, 10), pady=8)

        top_bar2 = ctk.CTkFrame(page)
        top_bar2.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.lbl_saved_count = ctk.CTkLabel(top_bar2, text="📚 Tổng số từ: 0", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_saved_count.pack(side="left", padx=12, pady=8)

        ctk.CTkButton(
            top_bar2,
            text="🎴 Học Flashcard (Thẻ Trắng)",
            width=210,
            height=34,
            fg_color="#4F46E5",
            hover_color="#4338CA",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_flashcard_modal
        ).pack(side="right", padx=10, pady=6)

        ctk.CTkButton(
            top_bar2,
            text="📤 Xuất Excel 9 Cột",
            width=155,
            height=34,
            fg_color="#0D7A5F",
            hover_color="#095945",
            command=self._export_saved_words_excel
        ).pack(side="right", padx=5, pady=6)

        ctk.CTkButton(
            top_bar2,
            text="📥 Nhập file Excel (Chuẩn 9 cột Stories)",
            width=250,
            height=34,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            font=ctk.CTkFont(weight="bold"),
            command=self._import_saved_words_excel
        ).pack(side="right", padx=5, pady=6)

        left_container = ctk.CTkFrame(page, fg_color="transparent")
        left_container.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        left_container.grid_rowconfigure(0, weight=1)
        left_container.grid_columnconfigure(0, weight=1)

        self.scroll_saved = ctk.CTkScrollableFrame(left_container)
        self.scroll_saved.grid(row=0, column=0, sticky="nsew")
        self.scroll_saved.grid_columnconfigure(0, weight=1)

        page_bar = ctk.CTkFrame(left_container, height=42)
        page_bar.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        ctk.CTkButton(page_bar, text="⏮ Đầu", width=65, height=28, command=self._first_saved_page).pack(side="left", padx=(8, 4), pady=6)
        ctk.CTkButton(page_bar, text="⬅ Trước", width=75, height=28, command=self._prev_saved_page).pack(side="left", padx=4, pady=6)

        self.lbl_pagination = ctk.CTkLabel(page_bar, text="Trang 1 / 1", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_pagination.pack(side="left", padx=14, pady=6)

        ctk.CTkButton(page_bar, text="Tiếp ➡", width=75, height=28, command=self._next_saved_page).pack(side="left", padx=4, pady=6)
        ctk.CTkButton(page_bar, text="Cuối ⏭", width=65, height=28, command=self._last_saved_page).pack(side="left", padx=4, pady=6)

        ctk.CTkButton(
            page_bar,
            text="🗑️ Xóa hết từ trong Folder này",
            width=190,
            height=28,
            fg_color="#C0392B",
            hover_color="#962D22",
            command=self._delete_all_words_in_current_folder
        ).pack(side="right", padx=8, pady=6)

        edit_frame = ctk.CTkFrame(page)
        edit_frame.grid(row=2, column=1, sticky="nsew", padx=(8, 0))
        edit_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(edit_frame, text="Thêm mới / Sửa từ vựng (Chuẩn 9 cột Stories)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, pady=(10, 8))

        fields = [
            ("1. Word:", "edit_word"),
            ("2. Pinyin:", "edit_pinyin"),
            ("3. Sino-Vietnamese:", "edit_hanviet"),
            ("4. Meaning:", "edit_meaning"),
            ("5. Example:", "edit_ex_zh"),
            ("6. Example Pinyin:", "edit_ex_py"),
            ("7. Example Translation:", "edit_ex_vi"),
            ("8. Level:", "edit_hsk"),
        ]
        self.edit_entries = {}
        for idx, (label_text, key) in enumerate(fields, start=1):
            ctk.CTkLabel(edit_frame, text=label_text, font=ctk.CTkFont(size=12)).grid(row=idx, column=0, sticky="w", padx=10, pady=4)
            ent = ctk.CTkEntry(edit_frame, font=("Microsoft YaHei UI", 13), height=28)
            ent.grid(row=idx, column=1, sticky="ew", padx=10, pady=4)
            self.edit_entries[key] = ent

        ctk.CTkLabel(edit_frame, text="9. Folder:", font=ctk.CTkFont(size=12)).grid(row=9, column=0, sticky="w", padx=10, pady=4)
        self.edit_topic_menu = ctk.CTkOptionMenu(edit_frame, values=database.get_all_topics(), height=28)
        self.edit_topic_menu.grid(row=9, column=1, sticky="ew", padx=10, pady=4)

        btn_box = ctk.CTkFrame(edit_frame, fg_color="transparent")
        btn_box.grid(row=10, column=0, columnspan=2, pady=12)

        ctk.CTkButton(btn_box, text="💾 Lưu / Cập nhật", width=125, fg_color="#0D7A5F", hover_color="#095945", command=self._save_edited_word).pack(side="left", padx=4)
        ctk.CTkButton(btn_box, text="Làm trống", width=95, fg_color="#6C757D", command=self._clear_edit_form).pack(side="left", padx=4)
        ctk.CTkButton(btn_box, text="Xóa từ", width=85, fg_color="#C0392B", hover_color="#962D22", command=self._delete_selected_word).pack(side="left", padx=4)

    def _on_search_or_filter_saved(self):
        self.saved_page_index = 1
        self._refresh_saved_words()

    def _first_saved_page(self):
        if self.saved_page_index > 1:
            self.saved_page_index = 1
            self._refresh_saved_words()

    def _prev_saved_page(self):
        if self.saved_page_index > 1:
            self.saved_page_index -= 1
            self._refresh_saved_words()

    def _next_saved_page(self):
        if self.saved_page_index < self.saved_total_pages:
            self.saved_page_index += 1
            self._refresh_saved_words()

    def _last_saved_page(self):
        if self.saved_page_index < self.saved_total_pages:
            self.saved_page_index = self.saved_total_pages
            self._refresh_saved_words()

    def _delete_all_words_in_current_folder(self):
        cur_topic = self.filter_topic_menu.get()
        msg = "Bạn có chắc muốn xóa TOÀN BỘ từ vựng trong tất cả các Folder không?" if cur_topic == "Tất cả" else f"Bạn có chắc muốn xóa toàn bộ từ vựng trong Folder [{cur_topic}] không?"
        if messagebox.askyesno("Xác nhận xóa từ vựng", msg):
            database.delete_words_by_topic(cur_topic)
            self.saved_page_index = 1
            self._refresh_saved_words()

    def _import_saved_words_excel(self):
        filepath = filedialog.askopenfilename(
            title="Chọn file Excel từ vựng (.xlsx)",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if not filepath:
            return

        use_sheet = messagebox.askyesno(
            "Tuỳ chọn phân loại Folder",
            "Bạn muốn lấy tên các Sheet ở dưới đáy file Excel (VD: vison, bài 41-bai 50, vision master) làm tên Folder,\n"
            "hay lấy theo cột 'Folder' (Cột I - VD: Camvision) trong bảng?\n\n"
            "• Bấm YES: Lấy tên từng Sheet làm Folder.\n"
            "• Bấm NO: Lấy theo cột 'Folder' (Cột I) trong bảng."
        )
        try:
            count, folders = database.import_words_from_excel(filepath, use_sheet_name_as_folder=use_sheet)
            self.saved_page_index = 1
            self._sync_topic_menus(selected_topic=folders[0] if len(folders) == 1 else "Tất cả")
            self._refresh_saved_words()
            messagebox.showinfo(
                "Nhập Excel thành công!",
                f"🎉 Đã nhập siêu tốc {count} từ vựng!\n"
                f"📁 Các Folder đã cập nhật: {', '.join(folders)}"
            )
        except Exception as e:
            messagebox.showerror("Lỗi nhập file Excel", f"Không thể đọc file Excel:\n{str(e)}")

    def _get_vocab_pool_for_learning(self, topic_filter="Tất cả") -> list:
        rows = database.get_saved_words(topic_filter=topic_filter)
        pool = []
        for r in rows:
            w_id, word, pinyin, hanviet, pos, meaning, hsk, w_topic, examples, notes, _, ex_zh, ex_py, ex_vi = r
            pool.append({
                "word": word,
                "pinyin": pinyin,
                "hanviet": hanviet,
                "pos": pos,
                "meaning": database.clean_meaning_text(meaning),
                "hsk": hsk or "abc",
                "topic": w_topic or "Camvision",
                "examples": examples,
                "example_zh": ex_zh,
                "example_pinyin": ex_py,
                "example_vi": ex_vi
            })
        return pool

    def _open_flashcard_modal(self):
        topic = self.filter_topic_menu.get()
        cards = self._get_vocab_pool_for_learning(topic_filter=topic)
        if not cards:
            cards = self._get_vocab_pool_for_learning(topic_filter="Tất cả")
        if not cards:
            messagebox.showwarning("Thông báo", "Chưa có từ vựng nào để ôn tập!")
            return

        win = ctk.CTkToplevel(self)
        win.title(f"🎴 Flashcard Từ Vựng - Folder: {topic}")
        win.geometry("620x660")
        win.minsize(580, 620)
        win.configure(fg_color="#F1F5F9")
        win.grab_set()

        state = {"idx": 0, "flipped": False, "cards": cards}

        top_bar = ctk.CTkFrame(win, fg_color="transparent")
        top_bar.pack(fill="x", padx=28, pady=(16, 6))

        badge_folder = ctk.CTkLabel(
            top_bar,
            text=f"  FOLDER: {topic.upper()}  ",
            font=("Segoe UI", 12, "bold"),
            fg_color="#E0E7FF",
            text_color="#4338CA",
            corner_radius=8,
            height=28
        )
        badge_folder.pack(side="left")

        lbl_progress = ctk.CTkLabel(
            top_bar,
            text="THẺ: 1 / 10",
            font=("Segoe UI", 12, "bold"),
            fg_color="#FCE7F3",
            text_color="#9333EA",
            corner_radius=8,
            height=28,
            padx=12
        )
        lbl_progress.pack(side="right")

        card = ctk.CTkFrame(
            win,
            fg_color="#FFFFFF",
            corner_radius=24,
            border_width=2,
            border_color="#E2E8F0"
        )
        card.pack(fill="both", expand=True, padx=28, pady=10)

        lbl_word = ctk.CTkLabel(
            card,
            text="",
            font=("Microsoft YaHei UI", 46, "bold"),
            text_color="#0F172A",
            wraplength=500
        )
        lbl_word.pack(pady=(24, 4), padx=16)

        lbl_pinyin = ctk.CTkLabel(
            card,
            text="",
            font=("Segoe UI", 22, "bold"),
            text_color="#10B981",
            wraplength=500
        )
        lbl_pinyin.pack(pady=(0, 14), padx=16)

        hv_box = ctk.CTkFrame(card, fg_color="#F8FAFC", corner_radius=14, border_width=1, border_color="#E2E8F0")
        hv_box.pack(pady=6, padx=50, fill="x")

        ctk.CTkLabel(hv_box, text="ÂM HÁN VIỆT", font=("Segoe UI", 11, "bold"), text_color="#94A3B8").pack(pady=(8, 0))
        lbl_hanviet = ctk.CTkLabel(hv_box, text="", font=("Segoe UI", 18, "bold"), text_color="#1E293B", wraplength=440)
        lbl_hanviet.pack(pady=(2, 10), padx=12)

        meaning_box = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=14, border_width=1, border_color="#C7D2FE")
        meaning_box.pack(pady=8, padx=50, fill="x")

        ctk.CTkLabel(meaning_box, text="NGHĨA TIẾNG VIỆT", font=("Segoe UI", 11, "bold"), text_color="#818CF8").pack(pady=(8, 0))
        lbl_meaning = ctk.CTkLabel(meaning_box, text="", font=("Segoe UI", 18, "bold"), text_color="#4F46E5", wraplength=440)
        lbl_meaning.pack(pady=(2, 10), padx=12)

        divider = ctk.CTkFrame(card, height=1, fg_color="#E2E8F0")
        divider.pack(fill="x", padx=40, pady=12)

        ctk.CTkLabel(card, text="VÍ DỤ CÁCH DÙNG", font=("Segoe UI", 11, "bold"), text_color="#CBD5E1").pack(pady=(0, 4))

        lbl_ex_py = ctk.CTkLabel(card, text="", font=("Segoe UI", 14, "bold"), text_color="#10B981", wraplength=480)
        lbl_ex_py.pack(padx=20)

        lbl_ex_zh = ctk.CTkLabel(card, text="", font=("Microsoft YaHei UI", 19, "bold"), text_color="#1E293B", wraplength=480)
        lbl_ex_zh.pack(pady=(2, 4), padx=20)

        lbl_ex_vi = ctk.CTkLabel(card, text="", font=("Segoe UI", 14, "italic"), text_color="#64748B", wraplength=480)
        lbl_ex_vi.pack(pady=(0, 14), padx=20)

        def render_card():
            c = state["cards"][state["idx"]]
            lbl_progress.configure(text=f"THẺ: {state['idx'] + 1} / {len(state['cards'])}")
            lbl_word.configure(text=c.get("word", ""))

            if not state["flipped"]:
                lbl_pinyin.configure(text="• • •  (Bấm Lật thẻ để xem đáp án)  • • •", text_color="#94A3B8", font=("Segoe UI", 14))
                lbl_hanviet.configure(text=(c.get("hanviet") or "N/A").upper())
                lbl_meaning.configure(text="???")
                lbl_ex_py.configure(text="")
                lbl_ex_zh.configure(text=c.get("example_zh") or "")
                lbl_ex_vi.configure(text="(Bấm vào thẻ hoặc nhấn phím Space để hiện Pinyin & Nghĩa)")
            else:
                lbl_pinyin.configure(text=c.get("pinyin", ""), text_color="#10B981", font=("Segoe UI", 22, "bold"))
                lbl_hanviet.configure(text=(c.get("hanviet") or "N/A").upper())
                lbl_meaning.configure(text=c.get("meaning", ""))
                lbl_ex_py.configure(text=c.get("example_pinyin", ""))
                lbl_ex_zh.configure(text=c.get("example_zh", ""))
                ex_v = c.get("example_vi", "")
                lbl_ex_vi.configure(text=f'"{ex_v}"' if ex_v else "")

        def flip_card():
            state["flipped"] = not state["flipped"]
            render_card()

        def prev_card():
            state["idx"] = (state["idx"] - 1) % len(state["cards"])
            state["flipped"] = False
            render_card()

        def next_card():
            state["idx"] = (state["idx"] + 1) % len(state["cards"])
            state["flipped"] = False
            render_card()

        for w in (card, lbl_word, lbl_pinyin, hv_box, meaning_box):
            w.bind("<Button-1>", lambda e: flip_card())

        win.bind("<space>", lambda e: flip_card())
        win.bind("<Left>", lambda e: prev_card())
        win.bind("<Right>", lambda e: next_card())

        ctrl = ctk.CTkFrame(win, fg_color="transparent")
        ctrl.pack(fill="x", padx=28, pady=(4, 18))

        ctk.CTkButton(ctrl, text="⬅ Trước", width=110, height=40, fg_color="#64748B", hover_color="#475569", command=prev_card).pack(side="left")
        ctk.CTkButton(
            ctrl,
            text="🔄 LẬT THẺ / XEM ĐÁP ÁN (Space)",
            height=40,
            fg_color="#4F46E5",
            hover_color="#4338CA",
            font=("Segoe UI", 14, "bold"),
            command=flip_card
        ).pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(ctrl, text="Tiếp ➡", width=110, height=40, fg_color="#0D7A5F", hover_color="#095945", command=next_card).pack(side="right")

        render_card()

    def _refresh_saved_words(self):
        for w in self.scroll_saved.winfo_children():
            w.destroy()

        query = self.entry_saved_search.get().strip()
        topic = self.filter_topic_menu.get()
        rows, total_count = database.get_saved_words_paginated(
            search_query=query,
            topic_filter=topic,
            page=self.saved_page_index,
            page_size=self.saved_page_size
        )

        self.saved_total_pages = max(1, math.ceil(total_count / self.saved_page_size))
        if self.saved_page_index > self.saved_total_pages:
            self.saved_page_index = self.saved_total_pages

        self.lbl_saved_count.configure(text=f"📚 Folder [{topic}]: Tổng {total_count} từ vựng (Hiển thị 20 từ/trang)")
        self.lbl_pagination.configure(text=f"Trang {self.saved_page_index} / {self.saved_total_pages}")

        if not rows:
            ctk.CTkLabel(
                self.scroll_saved,
                text="Chưa có từ vựng nào trong Folder này.\nHãy bấm '📥 Nhập file Excel' hoặc chọn Folder khác!",
                font=ctk.CTkFont(size=14)
            ).pack(pady=30)
            return

        for r in rows:
            w_id, word, pinyin, hanviet, pos, meaning, hsk, w_topic, examples, notes, created_at, ex_zh, ex_py, ex_vi = r
            card = ctk.CTkFrame(self.scroll_saved)
            card.pack(fill="x", padx=5, pady=4)
            card.grid_columnconfigure(0, weight=1)

            title_line = f"{word}   |   {pinyin}   |   {hanviet}   |   {meaning}"
            ctk.CTkLabel(card, text=title_line, font=("Microsoft YaHei UI", 14, "bold"), anchor="w", wraplength=540, justify="left").grid(row=0, column=0, sticky="w", padx=10, pady=(6, 2))

            sub_line = f"Ví dụ: {ex_zh}  ({ex_py})  →  {ex_vi}   [{w_topic} • Level: {hsk}]"
            ctk.CTkLabel(card, text=sub_line, font=("Microsoft YaHei UI", 12), justify="left", anchor="w", wraplength=540, text_color=("gray30", "gray70")).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))

            ctk.CTkButton(
                card,
                text="Chọn / Sửa",
                width=85,
                height=28,
                command=lambda row_data=r: self._load_word_into_form(row_data)
            ).grid(row=0, column=1, rowspan=2, padx=10, pady=6)

    def _load_word_into_form(self, row_data):
        w_id, word, pinyin, hanviet, pos, meaning, hsk, w_topic, examples, notes, _, ex_zh, ex_py, ex_vi = row_data
        self.selected_saved_word_id = w_id

        mapping = {
            "edit_word": word,
            "edit_pinyin": pinyin,
            "edit_hanviet": hanviet,
            "edit_meaning": database.clean_meaning_text(meaning),
            "edit_ex_zh": ex_zh,
            "edit_ex_py": ex_py,
            "edit_ex_vi": ex_vi,
            "edit_hsk": hsk
        }
        for k, val in mapping.items():
            self.edit_entries[k].delete(0, tk.END)
            self.edit_entries[k].insert(0, val or "")

        topics = database.get_all_topics()
        if w_topic in topics:
            self.edit_topic_menu.set(w_topic)

    def _clear_edit_form(self):
        self.selected_saved_word_id = None
        for ent in self.edit_entries.values():
            ent.delete(0, tk.END)

    def _save_edited_word(self):
        word = self.edit_entries["edit_word"].get().strip()
        if not word:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Word (Từ tiếng Trung)!")
            return

        pinyin = self.edit_entries["edit_pinyin"].get().strip() or ai_service.generate_local_pinyin(word)
        ex_zh = self.edit_entries["edit_ex_zh"].get().strip()
        ex_py = self.edit_entries["edit_ex_py"].get().strip() or ai_service.generate_local_pinyin(ex_zh)
        ex_vi = self.edit_entries["edit_ex_vi"].get().strip()

        database.save_word(
            word=word,
            pinyin=pinyin,
            hanviet=self.edit_entries["edit_hanviet"].get().strip(),
            pos="Từ vựng",
            meaning=self.edit_entries["edit_meaning"].get().strip(),
            hsk=self.edit_entries["edit_hsk"].get().strip() or "abc",
            topic=self.edit_topic_menu.get(),
            example_zh=ex_zh,
            example_pinyin=ex_py,
            example_vi=ex_vi
        )
        self._sync_topic_menus()
        self._refresh_saved_words()
        messagebox.showinfo("Thành công", f"Đã lưu cập nhật từ '{word}'!")

    def _delete_selected_word(self):
        if not self.selected_saved_word_id:
            messagebox.showwarning("Chưa chọn từ", "Hãy bấm nút 'Chọn / Sửa' ở một từ vựng bên trái trước khi xóa!")
            return
        if messagebox.askyesno("Xác nhận xóa", "Bạn có chắc muốn xóa từ vựng này khỏi sổ từ vựng không?"):
            database.delete_saved_word(self.selected_saved_word_id)
            self._clear_edit_form()
            self._refresh_saved_words()

    def _export_saved_words_excel(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="Stories_Camvision_9_Cot.xlsx"
        )
        if not filepath:
            return
        try:
            database.export_words_to_excel(filepath, topic_filter=self.filter_topic_menu.get())
            messagebox.showinfo("Xuất Excel thành công", f"Đã xuất danh sách từ vựng chuẩn 9 cột ra file:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Lỗi xuất Excel", str(e))

    # =========================================================================
    # TRANG 6: LINH ĐIỀN KÝ – TU TIÊN NÔNG TRẠI
    # =========================================================================
    def _build_farm_page(self):
        page = self.pages["farm"]
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        # PHẦN 1: TOP BAR TU TIÊN
        top_section = ctk.CTkFrame(page, fg_color="#183028", corner_radius=18)
        top_section.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top_section.grid_columnconfigure((0, 1, 2), weight=1)

        header_row = ctk.CTkFrame(top_section, fg_color="transparent")
        header_row.grid(row=0, column=0, columnspan=3, sticky="ew", padx=18, pady=(12, 8))

        ctk.CTkLabel(
            header_row,
            text="🌱 LINH ĐIỀN KÝ",
            font=("Segoe UI", 18, "bold"),
            text_color="#F1F5F9"
        ).pack(side="left")

        ctk.CTkLabel(header_row, text="  •  Thư mục (Folder) đang học:", font=("Segoe UI", 12, "bold"), text_color="#A7F3D0").pack(side="left", padx=(12, 4))
        self.farm_topic_menu = ctk.CTkOptionMenu(
            header_row,
            values=["Tất cả"] + database.get_all_topics(),
            width=145,
            height=28,
            fg_color="#26463B",
            button_color="#2D5A43",
            button_hover_color="#3B7A57",
            command=self._on_farm_folder_changed
        )
        self.farm_topic_menu.set("Camvision")
        self.farm_topic_menu.pack(side="left", padx=4)

        self.farm_plots_menu = ctk.CTkOptionMenu(
            header_row,
            values=["9 (3×3)", "12 (4×3)", "24 (4×6)"],
            width=95,
            height=28,
            fg_color="#26463B",
            button_color="#2D5A43"
        )
        self.farm_plots_menu.set("9 (3×3)")
        self.farm_plots_menu.pack(side="left", padx=4)

        ctk.CTkButton(
            header_row,
            text="Gieo lại Linh Điền",
            width=125,
            height=28,
            fg_color="#2D5A43",
            hover_color="#3B7A57",
            font=("Segoe UI", 12, "bold"),
            command=self._init_vocab_farm
        ).pack(side="left", padx=6)

        self.badge_cultivating = ctk.CTkLabel(
            header_row,
            text="  Đang tu luyện  ",
            font=("Segoe UI", 12, "bold"),
            fg_color="#1E4631",
            text_color="#4ADE80",
            corner_radius=10,
            height=26
        )
        self.badge_cultivating.pack(side="right")

        card_realm = ctk.CTkFrame(top_section, fg_color="#26463B", corner_radius=12)
        card_realm.grid(row=1, column=0, sticky="ew", padx=(18, 6), pady=4)
        ctk.CTkLabel(card_realm, text="Cảnh giới", font=("Segoe UI", 12), text_color="#94A3B8").pack(anchor="w", padx=14, pady=(8, 0))
        self.lbl_realm_val = ctk.CTkLabel(card_realm, text="Luyện Khí Tầng 3", font=("Segoe UI", 18, "bold"), text_color="#FFFFFF")
        self.lbl_realm_val.pack(anchor="w", padx=14, pady=(0, 8))

        card_energy = ctk.CTkFrame(top_section, fg_color="#26463B", corner_radius=12)
        card_energy.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(card_energy, text="Linh Khí", font=("Segoe UI", 12), text_color="#94A3B8").pack(anchor="w", padx=14, pady=(8, 0))
        self.lbl_energy_val = ctk.CTkLabel(card_energy, text="180 / 200", font=("Segoe UI", 18, "bold"), text_color="#FFFFFF")
        self.lbl_energy_val.pack(anchor="w", padx=14, pady=(0, 8))

        card_gold = ctk.CTkFrame(top_section, fg_color="#26463B", corner_radius=12)
        card_gold.grid(row=1, column=2, sticky="ew", padx=(6, 18), pady=4)
        ctk.CTkLabel(card_gold, text="Linh Thạch", font=("Segoe UI", 12), text_color="#94A3B8").pack(anchor="w", padx=14, pady=(8, 0))
        self.lbl_gold_val = ctk.CTkLabel(card_gold, text="1.250", font=("Segoe UI", 18, "bold"), text_color="#FFFFFF")
        self.lbl_gold_val.pack(anchor="w", padx=14, pady=(0, 8))

        tu_vi_row = ctk.CTkFrame(top_section, fg_color="transparent")
        tu_vi_row.grid(row=2, column=0, columnspan=3, sticky="ew", padx=18, pady=(4, 12))

        self.lbl_tu_vi_text = ctk.CTkLabel(tu_vi_row, text="Tu Vi: 320 / 500", font=("Segoe UI", 12, "bold"), text_color="#E2E8F0")
        self.lbl_tu_vi_text.pack(anchor="w", pady=(0, 4))

        self.prog_tu_vi = ctk.CTkProgressBar(tu_vi_row, height=8, corner_radius=4, fg_color="#26463B", progress_color="#86EFAC")
        self.prog_tu_vi.pack(fill="x")
        self.prog_tu_vi.set(0.64)

        # PHẦN 2: KHU VỰC LINH ĐIỀN CỦA BẠN
        mid_section = ctk.CTkFrame(page, fg_color="#EAE6DF", corner_radius=16)
        mid_section.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        mid_section.grid_columnconfigure((0, 1), weight=1)
        mid_section.grid_rowconfigure(1, weight=1)

        mid_header = ctk.CTkFrame(mid_section, fg_color="transparent")
        mid_header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(10, 4))

        self.lbl_farm_title = ctk.CTkLabel(
            mid_header,
            text="🌱 LINH ĐIỀN CỦA BẠN",
            font=("Segoe UI", 16, "bold"),
            text_color="#183028"
        )
        self.lbl_farm_title.pack(side="left")

        self.lbl_selected_plot_hint = ctk.CTkLabel(
            mid_header,
            text="  •  Đang chọn: Ô đất 01",
            font=("Segoe UI", 13, "bold"),
            text_color="#2D5A43"
        )
        self.lbl_selected_plot_hint.pack(side="left", padx=8)

        self.badge_grid_size = ctk.CTkLabel(
            mid_header,
            text="  3 × 3  ",
            font=("Segoe UI", 12, "bold"),
            fg_color="#CDE7D8",
            text_color="#166534",
            corner_radius=10,
            height=26
        )
        self.badge_grid_size.pack(side="right")

        self.scroll_farm_plots = ctk.CTkScrollableFrame(mid_section, fg_color="transparent")
        self.scroll_farm_plots.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=2)

        btn_water_main = ctk.CTkButton(
            mid_section,
            text="💧 Tưới nước",
            height=42,
            corner_radius=10,
            fg_color="#2D5A43",
            hover_color="#1E3F2E",
            text_color="#FFFFFF",
            font=("Segoe UI", 15, "bold"),
            command=self._water_selected_plot
        )
        btn_water_main.grid(row=2, column=0, sticky="ew", padx=(16, 6), pady=(6, 12))

        btn_harvest_main = ctk.CTkButton(
            mid_section,
            text="🌾 Thu hoạch",
            height=42,
            corner_radius=10,
            fg_color="#9E7332",
            hover_color="#7D5A25",
            text_color="#FFFFFF",
            font=("Segoe UI", 15, "bold"),
            command=self._harvest_selected_plot
        )
        btn_harvest_main.grid(row=2, column=1, sticky="ew", padx=(6, 16), pady=(6, 12))

        # PHẦN 3: TIÊN GIA CHỨC NĂNG
        bottom_section = ctk.CTkFrame(page, fg_color="#183028", corner_radius=18)
        bottom_section.grid(row=2, column=0, sticky="ew")
        bottom_section.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(
            bottom_section,
            text="TIÊN GIA CHỨC NĂNG",
            font=("Segoe UI", 12, "bold"),
            text_color="#CBD5E1"
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=18, pady=(10, 4))

        features = [
            ("⚔️\nTu luyện", self._open_cultivation_modal),
            ("🛍️\nBảo các", lambda: self._open_shop_modal(discount=1.0)),
            ("🎒\nTúi đồ", self._open_inventory_modal),
            ("🐾\nLinh thú", self._open_pets_modal),
            ("📜\nNhiệm vụ", self._open_quests_modal),
            ("⛰️\nBí cảnh", self._open_secret_realm_modal),
            ("🏆\nThành tựu", self._open_achievements_modal),
            ("📖\nNhật ký", self._open_logs_modal),
        ]

        self.feature_buttons = {}
        for idx, (f_text, f_cmd) in enumerate(features):
            r_i = (idx // 4) + 1
            c_i = idx % 4
            b = ctk.CTkButton(
                bottom_section,
                text=f_text,
                height=52,
                corner_radius=12,
                fg_color="#26463B",
                hover_color="#335C4E",
                text_color="#F8FAFC",
                font=("Segoe UI", 13, "bold"),
                command=f_cmd
            )
            b.grid(row=r_i, column=c_i, sticky="ew", padx=8, pady=5)
            self.feature_buttons[idx] = b

        ctk.CTkFrame(bottom_section, height=4, fg_color="transparent").grid(row=3, column=0, columnspan=4)

    def _on_farm_folder_changed(self, selected_folder: str):
        """Khi người chơi đổi Folder trên thanh Linh Điền, tự động nạp vocab_pool của Folder đó."""
        pool = self._get_vocab_pool_for_learning(topic_filter=selected_folder)
        if len(pool) < 4:
            messagebox.showwarning(
                "Số lượng từ vựng chưa đủ",
                f"Folder 【{selected_folder}】 hiện chỉ có {len(pool)} từ vựng (cần tối thiểu 4 từ để tạo câu hỏi).\n"
                f"Hãy thêm từ vào Folder này hoặc chọn Folder khác!"
            )
            return
        raw_plots_str = self.farm_plots_menu.get().split()[0]
        total_plots = int(raw_plots_str)
        self.farm_engine.dispatch("KHOI_TAO_GAME", {
            "folder_name": selected_folder,
            "vocab_pool": pool,
            "total_plots": total_plots
        })
        self._refresh_farm_ui()

    def _start_farm_background_ticker(self):
        def tick():
            if self.pages["farm"].winfo_ismapped():
                self._refresh_farm_ui()
            self.after(5000, tick)
        self.after(5000, tick)

    def _init_vocab_farm(self):
        topic = self.farm_topic_menu.get()
        pool = self._get_vocab_pool_for_learning(topic_filter=topic)
        if len(pool) < 4:
            messagebox.showwarning(
                "Chưa đủ từ vựng",
                f"Folder 【{topic}】 hiện chỉ có {len(pool)} từ vựng!\nCần ít nhất 4 từ vựng để sinh câu hỏi Kỳ Ngộ và Bí Cảnh."
            )
            return
        raw_plots_str = self.farm_plots_menu.get().split()[0]
        total_plots = int(raw_plots_str)

        res = self.farm_engine.dispatch("KHOI_TAO_GAME", {
            "folder_name": topic,
            "vocab_pool": pool,
            "total_plots": total_plots
        })
        self._refresh_farm_ui()
        messagebox.showinfo("Khai mở Linh Điền", res.get("message", ""))

    def _refresh_farm_ui(self):
        self._sync_farm_vocab_pool_from_selected_folder()
        state = self.farm_engine.get_state()
        if not state.get("plots"):
            pool = self._get_vocab_pool_for_learning(self.farm_topic_menu.get())
            self.farm_engine.dispatch("KHOI_TAO_GAME", {
                "folder_name": self.farm_topic_menu.get(),
                "vocab_pool": pool,
                "total_plots": 9
            })
            state = self.farm_engine.get_state()

        realm_name = state.get("realm_name", "Luyện Khí Tầng 3")
        tu_vi = state.get("tu_vi", 320)
        max_tu_vi = max(1, state.get("max_tu_vi", 500))
        energy = state.get("energy", 180)
        max_energy = state.get("max_energy", 200)
        gold = state.get("gold", 1250)

        active_pet_id = state.get("pets", {}).get("active_pet", "thanh_lan_loc")
        pet_info = VocabFarmEngine.SPIRIT_PETS.get(active_pet_id, {})
        pet_badge = f"  {pet_info.get('icon', '🦌')} {pet_info.get('name', '')} • Folder: {state.get('folder_name', 'Camvision')}  "

        self.badge_cultivating.configure(text=pet_badge)
        self.lbl_realm_val.configure(text=realm_name)
        self.lbl_energy_val.configure(text=f"{energy} / {max_energy}")
        self.lbl_gold_val.configure(text=f"{gold:,}".replace(",", "."))

        self.lbl_tu_vi_text.configure(text=f"Tu Vi: {tu_vi} / {max_tu_vi}")
        self.prog_tu_vi.set(min(1.0, tu_vi / max_tu_vi))

        if tu_vi >= max_tu_vi and 0 in self.feature_buttons:
            self.feature_buttons[0].configure(fg_color="#D97706", text="⚡\nĐỘT PHÁ!")
        elif 0 in self.feature_buttons:
            self.feature_buttons[0].configure(fg_color="#26463B", text="⚔️\nTu luyện")

        for w in self.scroll_farm_plots.winfo_children():
            w.destroy()

        plots = state.get("plots", {})
        total_p = len(plots)
        cols = 3 if total_p <= 9 else 4
        for c_i in range(4):
            self.scroll_farm_plots.grid_columnconfigure(c_i, weight=1 if c_i < cols else 0)

        rows_cnt = math.ceil(total_p / cols)
        self.badge_grid_size.configure(text=f"  {cols} × {rows_cnt}  ")

        now = time.time()
        for idx, (pid, pdata) in enumerate(sorted(plots.items(), key=lambda x: int(x[0]))):
            r_idx = idx // cols
            c_idx = idx % cols
            w_data = pdata.get("word_data")
            growth = pdata.get("growth", 0)
            is_vip = pdata.get("is_vip", False)
            cd_rem = max(0, int(pdata.get("cooldown_until", 0) - now))
            is_selected = (pid == self.selected_farm_plot_id)
            plot_num_str = f"Ô đất {int(pid)+1:02d}"

            if not w_data:
                icon = "🟫"
                status_txt = "Trống"
                bg_color = "#D8D4CC"
            else:
                if cd_rem > 0:
                    icon = "🥀"
                    status_txt = f"Héo ({cd_rem}s)"
                    bg_color = "#E5C6C3"
                elif growth <= 1:
                    icon = "🌱"
                    status_txt = f"{growth}/3"
                    bg_color = "#D3DEC8"
                elif growth == 2:
                    icon = "🌿"
                    status_txt = "2/3"
                    bg_color = "#C8DAB8"
                else:
                    icon = "🌳"
                    word_zh = w_data.get("word", "")
                    status_txt = f"3/3 • {word_zh}"
                    bg_color = "#B5D69C"

                if is_vip:
                    icon = "🌟" + icon

            border_w = 3 if is_selected else 0
            border_c = "#2D5A43" if is_selected else "#D3DEC8"

            card_btn = ctk.CTkButton(
                self.scroll_farm_plots,
                text=f"{icon}\n{plot_num_str}\n{status_txt}",
                height=86,
                corner_radius=14,
                border_width=border_w,
                border_color=border_c,
                fg_color=bg_color,
                hover_color="#C1D1B2",
                text_color="#183028",
                font=("Microsoft YaHei UI", 13, "bold"),
                command=lambda p=pid: self._select_farm_plot(p)
            )
            card_btn.grid(row=r_idx, column=c_idx, padx=6, pady=5, sticky="nsew")

        self._update_selected_plot_label()

    def _select_farm_plot(self, plot_id: str):
        self.selected_farm_plot_id = str(plot_id)
        self._refresh_farm_ui()

    def _update_selected_plot_label(self):
        state = self.farm_engine.get_state()
        p = state.get("plots", {}).get(self.selected_farm_plot_id)
        num_str = f"Ô đất {int(self.selected_farm_plot_id)+1:02d}"
        if not p or not p.get("word_data"):
            self.lbl_selected_plot_hint.configure(text=f"  •  Đang chọn: {num_str} (Trống - Bấm Tưới nước để gieo hạt)")
        else:
            g = p.get("growth", 0)
            if g >= 3:
                w = p["word_data"]
                self.lbl_selected_plot_hint.configure(text=f"  •  {num_str}: 🌳 Trưởng thành 【{w.get('word')} - {w.get('meaning')}】 (Sẵn sàng Thu hoạch!)")
            else:
                self.lbl_selected_plot_hint.configure(text=f"  •  {num_str}: Đang phát triển ({g}/3) — Bấm 'Tưới nước' để nuôi dưỡng")

    def _water_selected_plot(self):
        self._sync_farm_vocab_pool_from_selected_folder()
        res = self.farm_engine.dispatch("TUOI_NUOC", {"plot_id": self.selected_farm_plot_id})
        if not res.get("ok"):
            messagebox.showwarning("Linh Điền Ký", res.get("message", ""))
            return

        # Nếu kích hoạt Kỳ Ngộ (Random Event) thì hiện cửa sổ Kỳ Ngộ lấy từ vựng trong Folder
        if res.get("random_event"):
            self._open_random_event_modal(res["random_event"])
            return

        quiz = res.get("quiz")
        if quiz:
            self._open_simple_quiz_dialog(self.selected_farm_plot_id, quiz)
        else:
            self._refresh_farm_ui()
            messagebox.showinfo("Linh Điền Ký", res.get("message", ""))

    # =========================================================================
    # GIAO DIỆN CÂU HỎI TƯỚI NƯỚC (KHÔNG MẤT CHỮ + BÁO ĐÚNG/SAI RÕ RÀNG)
    # =========================================================================
    def _open_simple_quiz_dialog(self, plot_id: str, quiz: dict):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Tưới nước Linh Điền - Ôn tập từ vựng")
        dlg.geometry("680x560")
        dlg.minsize(640, 520)
        dlg.configure(fg_color="#FFFFFF")
        dlg.grab_set()

        selected_choice = [None]
        option_btns = {}
        submitted = [False]

        top_bar = ctk.CTkFrame(dlg, fg_color="transparent")
        top_bar.pack(fill="x", padx=28, pady=(18, 8))

        ctk.CTkButton(
            top_bar,
            text="‹",
            width=40,
            height=40,
            corner_radius=12,
            fg_color="#F8FAFC",
            hover_color="#E2E8F0",
            text_color="#64748B",
            border_width=1,
            border_color="#E2E8F0",
            font=("Segoe UI", 22),
            command=dlg.destroy
        ).pack(side="left")

        ctk.CTkLabel(
            top_bar,
            text=f"   {quiz.get('level_badge', 'ABC')}   ",
            fg_color="#EFF6FF",
            text_color="#4F46E5",
            corner_radius=12,
            height=30,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=12)

        ctk.CTkLabel(
            top_bar,
            text=f"   {quiz.get('stage_badge', 'PINYIN: 1 / 3')}   ",
            fg_color="#FDF2F8",
            text_color="#9333EA",
            corner_radius=12,
            height=30,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        ctk.CTkFrame(dlg, height=1, fg_color="#F1F5F9").pack(fill="x", padx=28, pady=(0, 12))

        main_text = quiz.get("main_display", "")
        main_font_size = 34 if len(main_text) <= 12 else (24 if len(main_text) <= 28 else 19)

        lbl_main = ctk.CTkLabel(
            dlg,
            text=main_text,
            font=("Microsoft YaHei UI", main_font_size, "bold"),
            text_color="#0F172A",
            wraplength=580,
            justify="center"
        )
        lbl_main.pack(pady=(6, 4), padx=24)

        lbl_hv = ctk.CTkLabel(
            dlg,
            text=quiz.get("hanviet_display", ""),
            font=("Segoe UI", 16, "italic"),
            text_color="#059669",
            wraplength=580
        )
        lbl_hv.pack(pady=(0, 4), padx=24)

        lbl_sub = ctk.CTkLabel(
            dlg,
            text=quiz.get("sub_display", ""),
            font=("Segoe UI", 15),
            text_color="#334155",
            wraplength=580,
            justify="center"
        )
        lbl_sub.pack(pady=(0, 14), padx=24)

        def finalize_submit(user_ans: str):
            if not user_ans or submitted[0]:
                return
            submitted[0] = True
            correct_ans = str(quiz.get("correct_answer", "")).strip()

            # Tô màu Đúng (Xanh lá) / Sai (Đỏ) trực tiếp trên các nút trước khi hiện thông báo
            for k_opt, b_widget in option_btns.items():
                if str(k_opt).strip().lower() == correct_ans.lower():
                    b_widget.configure(fg_color="#DCFCE7", border_color="#16A34A", text_color="#15803D", border_width=2)
                elif str(k_opt).strip().lower() == user_ans.strip().lower():
                    b_widget.configure(fg_color="#FEE2E2", border_color="#DC2626", text_color="#B91C1C", border_width=2)

            dlg.update()
            time.sleep(0.3)

            res = self.farm_engine.dispatch("TRA_LOI_QUIZ", {
                "plot_id": plot_id,
                "answer": user_ans,
                "correct_answer": correct_ans,
                "explanation": quiz.get("explanation"),
                "timeout": False
            })
            dlg.destroy()
            self._refresh_farm_ui()

            # Thông báo rõ ràng cho cả trường hợp ĐÚNG và SAI
            if res.get("correct"):
                messagebox.showinfo("🎉 Trả lời Chính xác!", res.get("message", ""))
            else:
                messagebox.showwarning("❌ Trả lời Chưa đúng!", res.get("message", ""))

        if quiz.get("mode") == "choice_2x2":
            grid_frame = ctk.CTkFrame(dlg, fg_color="transparent")
            grid_frame.pack(fill="x", padx=28, pady=6)
            grid_frame.grid_columnconfigure((0, 1), weight=1)

            btn_confirm = ctk.CTkButton(
                dlg,
                text="XÁC NHẬN",
                height=48,
                corner_radius=14,
                fg_color="#CBD5E1",
                hover_color="#4F46E5",
                text_color="#FFFFFF",
                font=("Segoe UI", 15, "bold"),
                state="disabled",
                command=lambda: finalize_submit(selected_choice[0])
            )

            def on_pick(opt_val: str):
                if submitted[0]:
                    return
                selected_choice[0] = opt_val
                for k_opt, b_widget in option_btns.items():
                    if k_opt == opt_val:
                        b_widget.configure(fg_color="#DBEAFE", border_color="#2563EB", border_width=2)
                    else:
                        b_widget.configure(fg_color="#F0F7FF", border_color="#DBEAFE", border_width=1)
                btn_confirm.configure(state="normal", fg_color="#4F46E5")

            for i, opt in enumerate(quiz.get("options", [])):
                r, c = i // 2, i % 2
                opt_str = str(opt)
                b = ctk.CTkButton(
                    grid_frame,
                    text=opt_str,
                    height=74,
                    corner_radius=14,
                    fg_color="#F0F7FF",
                    hover_color="#E0F2FE",
                    border_width=1,
                    border_color="#DBEAFE",
                    text_color="#1D4ED8",
                    font=("Microsoft YaHei UI", 17, "bold"),
                    command=lambda o=opt_str: on_pick(o)
                )
                b.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
                enable_button_wrap(b, wraplength=260, justify="center")
                option_btns[opt_str] = b

            btn_confirm.pack(fill="x", padx=36, pady=(12, 20), side="bottom")

        else:
            entry_ans = ctk.CTkEntry(
                dlg,
                placeholder_text="Nhập chữ Hán...",
                height=64,
                corner_radius=14,
                fg_color="#FFFFFF",
                border_width=2,
                border_color="#6366F1",
                text_color="#0F172A",
                font=("Microsoft YaHei UI", 22),
                justify="center"
            )
            entry_ans.pack(fill="x", padx=60, pady=(4, 8))
            entry_ans.focus_set()

            hint_btn = ctk.CTkButton(
                dlg,
                text=f"💡 Gợi ý chữ Hán: Điền nhanh ({quiz.get('correct_answer')})",
                fg_color="transparent",
                hover_color="#F1F5F9",
                text_color="#64748B",
                height=26,
                font=("Microsoft YaHei UI", 12),
                command=lambda: [entry_ans.delete(0, tk.END), entry_ans.insert(0, quiz.get("correct_answer", ""))]
            )
            hint_btn.pack(pady=2)

            btn_check = ctk.CTkButton(
                dlg,
                text="KIỂM TRA",
                height=48,
                corner_radius=14,
                fg_color="#4F46E5",
                hover_color="#4338CA",
                text_color="#FFFFFF",
                font=("Segoe UI", 15, "bold"),
                command=lambda: finalize_submit(entry_ans.get().strip())
            )
            btn_check.pack(fill="x", padx=60, pady=(10, 22), side="bottom")
            entry_ans.bind("<Return>", lambda e: finalize_submit(entry_ans.get().strip()))

    def _harvest_selected_plot(self):
        res = self.farm_engine.dispatch("THU_HOACH", {"plot_id": self.selected_farm_plot_id})
        self._refresh_farm_ui()
        if res.get("ok"):
            messagebox.showinfo("🌾 Thu hoạch Linh Thảo", res.get("message", ""))
        else:
            messagebox.showwarning("Chưa thể thu hoạch", res.get("message", ""))

    # =========================================================================
    # GIAO DIỆN SỰ KIỆN NGẪU NHIÊN (KỲ NGỘ) CHUẨN ẢNH MẪU NỀN KEM (#F4F1EA)
    # =========================================================================
    def _open_random_event_modal(self, ev: dict):
        if hasattr(self, "_event_win") and self._event_win and self._event_win.winfo_exists():
            return

        win = ctk.CTkToplevel(self)
        self._event_win = win
        win.title(f"{ev.get('icon', '🎁')} {ev.get('title', 'Kỳ Ngộ')}")
        win.geometry("680x650")
        win.minsize(640, 610)
        win.configure(fg_color="#F4F1EA")
        win.grab_set()

        selected_opt = [None]
        opt_buttons = {}
        answered = [False]

        # Khung nội dung chính
        container = ctk.CTkFrame(win, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=28, pady=18)

        # 1. Thiên Đạo nhắc nhở
        ctk.CTkLabel(
            container,
            text=f"Thiên Đạo nhắc nhở  •  {ev.get('icon', '🎁')} {ev.get('title', '')}",
            font=("Segoe UI", 16, "bold"),
            text_color="#1C2826"
        ).pack(anchor="w", pady=(0, 6))

        ctk.CTkLabel(
            container,
            text=ev.get("story", ""),
            font=("Segoe UI", 14),
            text_color="#2D3748",
            wraplength=610,
            justify="left"
        ).pack(anchor="w", pady=(0, 12))

        ctk.CTkFrame(container, height=1, fg_color="#D6D1C4").pack(fill="x", pady=6)

        # 2. Thử thách (Câu hỏi lấy từ Folder đang chọn)
        ctk.CTkLabel(
            container,
            text="Thử thách",
            font=("Segoe UI", 15, "bold"),
            text_color="#1C2826"
        ).pack(anchor="w", pady=(6, 4))

        ctk.CTkLabel(
            container,
            text=ev.get("prompt_title", ""),
            font=("Microsoft YaHei UI", 22, "bold"),
            text_color="#1E3F2E",
            wraplength=610,
            justify="left"
        ).pack(anchor="w", pady=(2, 4))

        ctk.CTkLabel(
            container,
            text=ev.get("sub_instruction", "Hãy chọn đáp án chính xác."),
            font=("Segoe UI", 13),
            text_color="#64748B",
            wraplength=610,
            justify="left"
        ).pack(anchor="w", pady=(0, 10))

        # 3. 4 Thẻ Đáp án A, B, C, D (Tự động xuống dòng không mất chữ)
        opts_frame = ctk.CTkFrame(container, fg_color="transparent")
        opts_frame.pack(fill="x", pady=4)

        btn_confirm = ctk.CTkButton(
            container,
            text="Xác nhận lựa chọn",
            height=46,
            corner_radius=22,
            fg_color="#94A3B8",
            hover_color="#15803D",
            text_color="#FFFFFF",
            font=("Segoe UI", 15, "bold"),
            state="disabled"
        )

        def select_option(opt_val: str):
            if answered[0]:
                return
            selected_opt[0] = opt_val
            for k_val, b_info in opt_buttons.items():
                if k_val == opt_val:
                    b_info["btn"].configure(fg_color="#DCFCE7", border_color="#15803D", border_width=2, text_color="#14532D")
                else:
                    b_info["btn"].configure(fg_color="#FFFFFF", border_color="#E2DFD7", border_width=1, text_color="#1E293B")
            btn_confirm.configure(state="normal", fg_color="#15803D")

        letters = ["A", "B", "C", "D"]
        for idx, opt_text in enumerate(ev.get("options", [])):
            letter = letters[idx] if idx < len(letters) else str(idx + 1)
            display_str = f"  {letter}.   {opt_text}"
            b = ctk.CTkButton(
                opts_frame,
                text=display_str,
                anchor="w",
                height=52,
                corner_radius=12,
                fg_color="#FFFFFF",
                hover_color="#EAF4EC",
                border_width=1,
                border_color="#E2DFD7",
                text_color="#1E293B",
                font=("Microsoft YaHei UI", 15, "bold"),
                command=lambda v=opt_text: select_option(v)
            )
            b.pack(fill="x", pady=5)
            enable_button_wrap(b, wraplength=560, justify="left")
            opt_buttons[opt_text] = {"btn": b, "letter": letter}

        ctk.CTkFrame(container, height=1, fg_color="#D6D1C4").pack(fill="x", pady=(10, 8))

        # 4. Phần thưởng
        rw_row = ctk.CTkFrame(container, fg_color="transparent")
        rw_row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(rw_row, text="Phần thưởng", font=("Segoe UI", 15, "bold"), text_color="#854D0E").pack(side="left")
        ctk.CTkLabel(rw_row, text=ev.get("reward_text", "+100 Linh Thạch"), font=("Segoe UI", 15, "bold"), text_color="#0F172A").pack(side="right")

        def confirm_event_answer():
            if not selected_opt[0] or answered[0]:
                return
            answered[0] = True
            chosen = selected_opt[0]
            correct_val = ev.get("correct", "")

            for k_val, b_info in opt_buttons.items():
                if k_val == correct_val:
                    b_info["btn"].configure(fg_color="#DCFCE7", border_color="#16A34A", text_color="#15803D", border_width=2)
                elif k_val == chosen:
                    b_info["btn"].configure(fg_color="#FEE2E2", border_color="#DC2626", text_color="#B91C1C", border_width=2)

            win.update()
            time.sleep(0.35)

            res = self.farm_engine.dispatch("GIAI_QUYET_SU_KIEN", {"answer": chosen})
            win.destroy()
            self._refresh_farm_ui()

            if res.get("correct"):
                messagebox.showinfo("✨ Kỳ Ngộ Viên Mãn (Trả lời ĐÚNG)!", res.get("message", ""))
                if res.get("open_merchant_discount"):
                    self._open_shop_modal(discount=0.5)
            else:
                messagebox.showwarning("💨 Kỳ Ngộ Thất Bại (Trả lời SAI)!", res.get("message", ""))

        btn_confirm.configure(command=confirm_event_answer)
        btn_confirm.pack(fill="x", pady=(4, 4))

    # =========================================================================
    # 6. ⛰️ BẢN ĐỒ BÍ CẢNH & HÀNH TRÌNH KHÁM PHÁ (CHUẨN ẢNH MẪU)
    # =========================================================================
    def _open_secret_realm_modal(self):
        self._sync_farm_vocab_pool_from_selected_folder()
        state = self.farm_engine.get_state()
        pool = state.get("vocab_pool", [])

        if len(pool) < 4:
            messagebox.showwarning(
                "Chưa đủ từ vựng",
                f"Folder 【{state.get('folder_name')}】 hiện chỉ có {len(pool)} từ vựng!\nCần ít nhất 4 từ vựng để mở Bản Đồ Bí Cảnh."
            )
            return

        win = ctk.CTkToplevel(self)
        win.title("⛰️ Bản Đồ Bí Cảnh")
        win.geometry("740x620")
        win.minsize(700, 580)
        win.configure(fg_color="#F8FAFC")
        win.grab_set()

        # Header Bản Đồ Bí Cảnh
        header = ctk.CTkFrame(win, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(20, 10))

        ctk.CTkLabel(
            header,
            text=f"BẢN ĐỒ BÍ CẢNH  (Nguồn từ vựng: {state.get('folder_name')})",
            font=("Segoe UI", 18, "bold"),
            text_color="#0F172A"
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="  3 khu vực  ",
            font=("Segoe UI", 12, "bold"),
            fg_color="#DCFCE7",
            text_color="#15803D",
            corner_radius=12,
            height=28
        ).pack(side="right")

        scroll = ctk.CTkScrollableFrame(win, fg_color="#FFFFFF", corner_radius=16, border_width=1, border_color="#E2E8F0")
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        scroll.grid_columnconfigure(0, weight=1)

        cur_realm_idx = state.get("realm_idx", 0)
        realm_icons = {"thanh_van": "🌲", "u_minh": "🏯", "cuu_u": "🌋"}
        realm_bg_colors = {"thanh_van": "#0D9488", "u_minh": "#4338CA", "cuu_u": "#991B1B"}

        for r_cfg in VocabFarmEngine.SECRET_REALMS:
            rid = r_cfg["id"]
            unlocked = cur_realm_idx >= r_cfg["req_realm_idx"]

            card = ctk.CTkFrame(scroll, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#E2E8F0")
            card.pack(fill="x", padx=12, pady=8)
            card.grid_columnconfigure(1, weight=1)

            # Khung đại diện hình ảnh Bí Cảnh bên trái
            art_box = ctk.CTkFrame(
                card,
                width=110,
                height=110,
                corner_radius=14,
                fg_color=realm_bg_colors.get(rid, "#1E293B")
            )
            art_box.grid(row=0, column=0, rowspan=4, padx=14, pady=14)
            art_box.grid_propagate(False)
            ctk.CTkLabel(art_box, text=realm_icons.get(rid, "⛰️"), font=("Segoe UI", 42)).place(relx=0.5, rely=0.5, anchor="center")

            # Thông tin chi tiết bên phải
            title_row = ctk.CTkFrame(card, fg_color="transparent")
            title_row.grid(row=0, column=1, sticky="w", padx=6, pady=(14, 2))

            ctk.CTkLabel(title_row, text=r_cfg["name"], font=("Segoe UI", 17, "bold"), text_color="#0F172A").pack(side="left")
            ctk.CTkLabel(
                title_row,
                text=f"  {r_cfg['difficulty']}  ",
                font=("Segoe UI", 12, "bold"),
                fg_color=r_cfg["diff_color"],
                text_color=r_cfg["diff_text_color"],
                corner_radius=8
            ).pack(side="left", padx=10)

            ctk.CTkLabel(
                card,
                text=f"Cảnh giới đề xuất: {r_cfg['req_realm_name']}  •  Số khu vực: {r_cfg['areas_count']} cửa ải  •  Boss: {r_cfg['boss_name']}",
                font=("Segoe UI", 13),
                text_color="#64748B"
            ).grid(row=1, column=1, sticky="w", padx=6, pady=1)

            ctk.CTkLabel(
                card,
                text=r_cfg["desc"],
                font=("Segoe UI", 14),
                text_color="#1E293B",
                wraplength=400,
                justify="left"
            ).grid(row=2, column=1, sticky="w", padx=6, pady=2)

            ctk.CTkLabel(
                card,
                text=r_cfg["reward_desc"],
                font=("Segoe UI", 13, "bold"),
                text_color="#16A34A"
            ).grid(row=3, column=1, sticky="w", padx=6, pady=(2, 14))

            # Nút Khám phá hoặc Khóa
            if unlocked:
                btn_explore = ctk.CTkButton(
                    card,
                    text="Khám phá ➡",
                    width=125,
                    height=38,
                    corner_radius=10,
                    fg_color="#15803D",
                    hover_color="#166534",
                    font=("Segoe UI", 13, "bold"),
                    command=lambda rc=r_cfg: [win.destroy(), self._start_secret_realm_expedition(rc)]
                )
            else:
                btn_explore = ctk.CTkButton(
                    card,
                    text=f"🔒 Cần {r_cfg['req_realm_name']}",
                    width=125,
                    height=38,
                    corner_radius=10,
                    fg_color="#CBD5E1",
                    text_color="#475569",
                    state="disabled",
                    font=("Segoe UI", 12, "bold")
                )
            btn_explore.grid(row=0, column=2, rowspan=4, padx=14, pady=14)

    def _start_secret_realm_expedition(self, realm_cfg: dict):
        """
        Chế độ Khám phá Bí Cảnh qua từng khu vực + Đấu Boss cuối + Màn hình tổng kết.
        Tất cả câu hỏi đều lấy từ vocab_pool của Folder đang chọn và không lặp từ.
        """
        state = self.farm_engine.get_state()
        pool = state.get("vocab_pool", [])
        stages = realm_cfg["stages"]

        run_state = {
            "stage_idx": 0,
            "player_hp": 100,
            "max_player_hp": 100,
            "boss_hp": realm_cfg["boss_hp"],
            "max_boss_hp": realm_cfg["boss_hp"],
            "correct_count": 0,
            "wrong_count": 0,
            "bonus_gold": 0,
            "used_words": set(),
            "start_time": time.time()
        }

        win = ctk.CTkToplevel(self)
        win.title(f"⛰️ Đang khám phá: {realm_cfg['name']}")
        win.geometry("720x660")
        win.minsize(680, 620)
        win.configure(fg_color="#F4F1EA")
        win.grab_set()

        # Thanh trạng thái HP người chơi & Tiến độ khu vực
        top_bar = ctk.CTkFrame(win, fg_color="#183028", corner_radius=14)
        top_bar.pack(fill="x", padx=20, pady=(16, 8))

        lbl_stage_name = ctk.CTkLabel(top_bar, text="", font=("Segoe UI", 16, "bold"), text_color="#FBBF24")
        lbl_stage_name.pack(anchor="w", padx=16, pady=(10, 2))

        hp_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        hp_row.pack(fill="x", padx=16, pady=(2, 10))

        lbl_player_hp = ctk.CTkLabel(hp_row, text="❤️ HP Người chơi: 100 / 100", font=("Segoe UI", 13, "bold"), text_color="#4ADE80")
        lbl_player_hp.pack(side="left")

        lbl_boss_hp = ctk.CTkLabel(hp_row, text="", font=("Segoe UI", 13, "bold"), text_color="#F87171")
        lbl_boss_hp.pack(side="right")

        # Khung nội dung câu hỏi / tổng kết
        body_frame = ctk.CTkFrame(win, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, padx=24, pady=8)

        def render_expedition_step():
            for w in body_frame.winfo_children():
                w.destroy()

            # Kiểm tra thua cuộc
            if run_state["player_hp"] <= 0:
                render_summary_screen(victory=False)
                return

            # Kiểm tra đã vượt hết các khu vực
            if run_state["stage_idx"] >= len(stages):
                render_summary_screen(victory=True)
                return

            st_cfg = stages[run_state["stage_idx"]]
            is_boss = (st_cfg["type"] == "boss")

            lbl_stage_name.configure(text=f"📍 {st_cfg['name']}  ({run_state['stage_idx'] + 1}/{len(stages)})")
            lbl_player_hp.configure(text=f"❤️ HP của bạn: {run_state['player_hp']} / {run_state['max_player_hp']}")
            if is_boss:
                lbl_boss_hp.configure(text=f"🐉 {realm_cfg['boss_name']} HP: {run_state['boss_hp']} / {run_state['max_boss_hp']}")
            else:
                lbl_boss_hp.configure(text=f"💰 Nhặt được: +{run_state['bonus_gold']} Linh Thạch")

            # Nếu sử dụng hết từ trong pool thì làm mới bộ lọc chống lặp
            if len(run_state["used_words"]) >= len(pool):
                run_state["used_words"].clear()

            q_type = st_cfg["q_type"]
            if q_type == "mix":
                q_type = random.choice(["zh_to_vi", "vi_to_zh", "zh_to_py", "fill_blank"])

            q_data = self.farm_engine.build_pool_question(pool, q_type=q_type, exclude_words=run_state["used_words"])
            run_state["used_words"].add(q_data["word"])

            ctk.CTkLabel(
                body_frame,
                text=st_cfg["story"],
                font=("Segoe UI", 14),
                text_color="#334155",
                wraplength=640,
                justify="left"
            ).pack(anchor="w", pady=(4, 10))

            q_card = ctk.CTkFrame(body_frame, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#D6D1C4")
            q_card.pack(fill="x", pady=6)

            ctk.CTkLabel(
                q_card,
                text=q_data["prompt_title"],
                font=("Microsoft YaHei UI", 21, "bold"),
                text_color="#183028",
                wraplength=610,
                justify="left"
            ).pack(anchor="w", padx=18, pady=(14, 4))

            ctk.CTkLabel(
                q_card,
                text=q_data["sub_instruction"],
                font=("Segoe UI", 13),
                text_color="#64748B",
                wraplength=610,
                justify="left"
            ).pack(anchor="w", padx=18, pady=(0, 14))

            lbl_feedback = ctk.CTkLabel(
                body_frame,
                text="Hãy chọn đáp án rồi bấm Xác nhận:",
                font=("Segoe UI", 14, "bold"),
                text_color="#475569",
                wraplength=640,
                justify="left"
            )
            lbl_feedback.pack(anchor="w", pady=(8, 4))

            opts_box = ctk.CTkFrame(body_frame, fg_color="transparent")
            opts_box.pack(fill="x", pady=4)

            picked = [None]
            step_btns = {}
            step_locked = [False]

            btn_action = ctk.CTkButton(
                body_frame,
                text="Xác nhận lựa chọn",
                height=44,
                corner_radius=20,
                fg_color="#94A3B8",
                text_color="#FFFFFF",
                font=("Segoe UI", 15, "bold"),
                state="disabled"
            )

            def on_select_opt(val: str):
                if step_locked[0]:
                    return
                picked[0] = val
                for k_v, b_w in step_btns.items():
                    if k_v == val:
                        b_w.configure(fg_color="#DCFCE7", border_color="#15803D", border_width=2)
                    else:
                        b_w.configure(fg_color="#FFFFFF", border_color="#E2DFD7", border_width=1)
                btn_action.configure(state="normal", fg_color="#15803D")

            letters = ["A", "B", "C", "D"]
            for idx_o, opt_val in enumerate(q_data["options"]):
                lt = letters[idx_o] if idx_o < 4 else str(idx_o + 1)
                b = ctk.CTkButton(
                    opts_box,
                    text=f"  {lt}.   {opt_val}",
                    anchor="w",
                    height=50,
                    corner_radius=12,
                    fg_color="#FFFFFF",
                    hover_color="#EAF4EC",
                    border_width=1,
                    border_color="#E2DFD7",
                    text_color="#0F172A",
                    font=("Microsoft YaHei UI", 15, "bold"),
                    command=lambda v=opt_val: on_select_opt(v)
                )
                b.pack(fill="x", pady=4)
                enable_button_wrap(b, wraplength=580, justify="left")
                step_btns[opt_val] = b

            def submit_step():
                if not picked[0] or step_locked[0]:
                    return
                step_locked[0] = True
                user_v = picked[0]
                corr_v = q_data["correct_answer"]
                is_right = (user_v == corr_v)

                for k_v, b_w in step_btns.items():
                    if k_v == corr_v:
                        b_w.configure(fg_color="#DCFCE7", border_color="#16A34A", text_color="#15803D", border_width=2)
                    elif k_v == user_v:
                        b_w.configure(fg_color="#FEE2E2", border_color="#DC2626", text_color="#B91C1C", border_width=2)

                if is_right:
                    run_state["correct_count"] += 1
                    if is_boss:
                        run_state["boss_hp"] = max(0, run_state["boss_hp"] - 30)
                        fb_msg = f"✅ CHÍNH XÁC! Gây 30 sát thương lên {realm_cfg['boss_name']}! ({q_data['word']}: {q_data['meaning']})"
                        if run_state["boss_hp"] <= 0:
                            run_state["stage_idx"] += 1
                    else:
                        run_state["bonus_gold"] += 20
                        run_state["stage_idx"] += 1
                        fb_msg = f"✅ CHÍNH XÁC! Vượt qua cửa ải & nhặt được +20 Linh Thạch! ({q_data['word']}: {q_data['meaning']})"
                    lbl_feedback.configure(text=fb_msg, text_color="#15803D")
                else:
                    run_state["wrong_count"] += 1
                    dmg = st_cfg["hp_pen"]
                    run_state["player_hp"] = max(0, run_state["player_hp"] - dmg)
                    if not is_boss:
                        run_state["stage_idx"] += 1
                    fb_msg = f"❌ CHƯA ĐÚNG! Đáp án đúng là: “{corr_v}”. Bạn bị mất -{dmg} HP!"
                    lbl_feedback.configure(text=fb_msg, text_color="#DC2626")

                lbl_player_hp.configure(text=f"❤️ HP của bạn: {run_state['player_hp']} / {run_state['max_player_hp']}")
                if is_boss:
                    lbl_boss_hp.configure(text=f"🐉 {realm_cfg['boss_name']} HP: {run_state['boss_hp']} / {run_state['max_boss_hp']}")

                btn_action.configure(
                    text="Tiếp tục hành trình ➡",
                    fg_color="#2563EB",
                    command=render_expedition_step
                )

            btn_action.configure(command=submit_step)
            btn_action.pack(fill="x", pady=(10, 4))

        def render_summary_screen(victory: bool):
            elapsed_sec = int(time.time() - run_state["start_time"])
            res = self.farm_engine.dispatch("HOAN_THANH_BI_CANH", {
                "realm_id": realm_cfg["id"],
                "victory": victory,
                "correct_count": run_state["correct_count"],
                "wrong_count": run_state["wrong_count"],
                "bonus_gold": run_state["bonus_gold"]
            })
            self._refresh_farm_ui()

            lbl_stage_name.configure(text=f"🏁 KẾT THÚC BÍ CẢNH: {realm_cfg['name'].upper()}")
            card = ctk.CTkFrame(body_frame, fg_color="#FFFFFF", corner_radius=16, border_width=2, border_color="#16A34A" if victory else "#DC2626")
            card.pack(fill="both", expand=True, pady=12)

            title_t = "🏆 KHÁM PHÁ ĐẠI THÀNH CÔNG!" if victory else "💨 KHÁM PHÁ THẤT BẠI"
            ctk.CTkLabel(card, text=title_t, font=("Segoe UI", 22, "bold"), text_color="#15803D" if victory else "#B91C1C").pack(pady=(24, 10))

            summary_txt = (
                f"{res.get('message', '')}\n\n"
                f"• Số cửa ải đã vượt qua: {run_state['stage_idx']} / {len(stages)}\n"
                f"• HP còn lại: {run_state['player_hp']} / 100\n"
                f"• Thời gian khám phá: {elapsed_sec} giây"
            )
            ctk.CTkLabel(card, text=summary_txt, font=("Segoe UI", 15), text_color="#1E293B", justify="left", wraplength=560).pack(pady=10, padx=24)

            btn_row = ctk.CTkFrame(card, fg_color="transparent")
            btn_row.pack(pady=20)

            ctk.CTkButton(
                btn_row,
                text="🔄 Khám phá lại",
                width=160,
                height=42,
                fg_color="#2563EB",
                font=("Segoe UI", 14, "bold"),
                command=lambda: [win.destroy(), self._start_secret_realm_expedition(realm_cfg)]
            ).pack(side="left", padx=10)

            ctk.CTkButton(
                btn_row,
                text="🌱 Trở về Linh Điền",
                width=170,
                height=42,
                fg_color="#15803D",
                font=("Segoe UI", 14, "bold"),
                command=win.destroy
            ).pack(side="left", padx=10)

        render_expedition_step()

    # =========================================================================
    # CÁC CHỨC NĂNG TIÊN GIA KHÁC (TU LUYỆN, BẢO CÁC, TÚI ĐỒ, LINH THÚ, NHIỆM VỤ...)
    # =========================================================================
    def _open_cultivation_modal(self):
        state = self.farm_engine.get_state()
        win = ctk.CTkToplevel(self)
        win.title("⚔️ Tu Luyện & Đột Phá Cảnh Giới")
        win.geometry("560x460")
        win.configure(fg_color="#183028")
        win.grab_set()

        ctk.CTkLabel(win, text="⚔️ ĐẠO ĐÀI TU LUYỆN", font=("Segoe UI", 20, "bold"), text_color="#FBBF24").pack(pady=(20, 10))

        card = ctk.CTkFrame(win, fg_color="#26463B", corner_radius=16)
        card.pack(fill="x", padx=28, pady=10)

        ctk.CTkLabel(card, text=f"Đạo hiệu: {state['profile_name']}", font=("Segoe UI", 15, "bold"), text_color="#A7F3D0").pack(pady=(14, 4))
        ctk.CTkLabel(card, text=f"Cảnh giới hiện tại: {state['realm_name']}", font=("Segoe UI", 18, "bold"), text_color="#FFFFFF").pack(pady=4)
        ctk.CTkLabel(card, text=f"Tu Vi tích lũy: {state['tu_vi']} / {state['max_tu_vi']}", font=("Segoe UI", 15), text_color="#E2E8F0").pack(pady=4)
        ctk.CTkLabel(card, text=f"Số lần đột phá thành công: {state.get('breakthrough_count', 0)} lần", font=("Segoe UI", 13), text_color="#94A3B8").pack(pady=(2, 14))

        can_break = state["tu_vi"] >= state["max_tu_vi"]
        status_msg = "✨ Linh khí đã viên mãn! Có thể tiến hành ĐỘT PHÁ ngay!" if can_break else f"Cần tích lũy thêm {state['max_tu_vi'] - state['tu_vi']} Tu Vi nữa để đột phá."
        ctk.CTkLabel(win, text=status_msg, font=("Segoe UI", 14, "bold"), text_color="#4ADE80" if can_break else "#FBBF24").pack(pady=10)

        def do_breakthrough():
            res = self.farm_engine.dispatch("DOT_PHA", {"passed_tribulation": True})
            self._refresh_farm_ui()
            win.destroy()
            if res.get("ok"):
                messagebox.showinfo("⚡ Đột Phá Thành Công", res.get("message", ""))
            else:
                messagebox.showwarning("Chưa đủ điều kiện", res.get("message", ""))

        ctk.CTkButton(
            win,
            text="⚡ ĐỘT PHÁ CẢNH GIỚI TIẾP THEO",
            height=46,
            corner_radius=12,
            fg_color="#D97706" if can_break else "#475569",
            hover_color="#B45309",
            font=("Segoe UI", 15, "bold"),
            command=do_breakthrough
        ).pack(fill="x", padx=40, pady=15)

    def _open_shop_modal(self, discount: float = 1.0):
        win = ctk.CTkToplevel(self)
        title_str = "🏮 Thương Nhân Bí Ẩn (Ưu đãi Giảm 50%!)" if discount < 1.0 else "🛍️ Tàng Bảo Các – Cửa Hàng Pháp Bảo & Đan Dược"
        win.title(title_str)
        win.geometry("680x560")
        win.configure(fg_color="#183028")
        win.grab_set()

        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(16, 8))
        ctk.CTkLabel(top, text=title_str, font=("Segoe UI", 18, "bold"), text_color="#FBBF24").pack(side="left")
        lbl_gold = ctk.CTkLabel(top, text="", font=("Segoe UI", 15, "bold"), text_color="#4ADE80")
        lbl_gold.pack(side="right")

        scroll = ctk.CTkScrollableFrame(win, fg_color="#26463B", corner_radius=14)
        scroll.pack(fill="both", expand=True, padx=24, pady=(4, 18))
        scroll.grid_columnconfigure(0, weight=1)

        def render_shop():
            state = self.farm_engine.get_state()
            lbl_gold.configure(text=f"Linh Thạch: {state['gold']:,}".replace(",", "."))
            for w in scroll.winfo_children():
                w.destroy()

            inv = state.get("inventory", {})
            for item_id, info in VocabFarmEngine.SHOP_ITEMS.items():
                base_p = info["price"]
                if item_id == "mo_o_dat":
                    base_p = 100 * (state.get("land_expand_count", 0) + 1)
                price = max(1, int(base_p * discount))
                owned_cnt = inv.get(item_id, 0)

                card = ctk.CTkFrame(scroll, fg_color="#183028", corner_radius=12)
                card.pack(fill="x", padx=8, pady=6)
                card.grid_columnconfigure(0, weight=1)

                title_t = f"{info['icon']}  {info['name']}   [{info['category']}]   —   Đang có: {owned_cnt}"
                ctk.CTkLabel(card, text=title_t, font=("Segoe UI", 15, "bold"), text_color="#FFFFFF").grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2))
                ctk.CTkLabel(card, text=f"{info['desc']}\nCông dụng: {info['effect']}", font=("Segoe UI", 12), text_color="#A7F3D0", justify="left", wraplength=420).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))

                ctk.CTkButton(
                    card,
                    text=f"Mua ({price} Linh Thạch)",
                    width=165,
                    height=36,
                    fg_color="#9E7332",
                    hover_color="#7D5A25",
                    font=("Segoe UI", 13, "bold"),
                    command=lambda iid=item_id: buy_item(iid)
                ).grid(row=0, column=1, rowspan=2, padx=14, pady=10)

        def buy_item(iid: str):
            res = self.farm_engine.dispatch("MUA_HANG", {"item_id": iid, "discount": discount})
            render_shop()
            self._refresh_farm_ui()
            if res.get("ok"):
                messagebox.showinfo("Tàng Bảo Các", res.get("message", ""))
            else:
                messagebox.showwarning("Tàng Bảo Các", res.get("message", ""))

        render_shop()

    def _open_inventory_modal(self):
        win = ctk.CTkToplevel(self)
        win.title("🎒 Túi Đồ Tu Tiên")
        win.geometry("640x520")
        win.configure(fg_color="#183028")
        win.grab_set()

        ctk.CTkLabel(win, text="🎒 TÚI CÀN KHÔN (TÚI ĐỒ)", font=("Segoe UI", 19, "bold"), text_color="#FBBF24").pack(pady=(16, 4))
        ctk.CTkLabel(win, text=f"Vật phẩm pháp bảo sẽ tác dụng lên Ô đất đang chọn: Ô #{int(self.selected_farm_plot_id)+1:02d}", font=("Segoe UI", 13), text_color="#A7F3D0").pack(pady=(0, 8))

        scroll = ctk.CTkScrollableFrame(win, fg_color="#26463B", corner_radius=14)
        scroll.pack(fill="both", expand=True, padx=24, pady=(4, 18))

        def render_inv():
            state = self.farm_engine.get_state()
            inv = state.get("inventory", {})
            for w in scroll.winfo_children():
                w.destroy()

            has_any = False
            for item_id, cnt in inv.items():
                if cnt <= 0 or item_id not in VocabFarmEngine.SHOP_ITEMS:
                    continue
                has_any = True
                info = VocabFarmEngine.SHOP_ITEMS[item_id]
                card = ctk.CTkFrame(scroll, fg_color="#183028", corner_radius=12)
                card.pack(fill="x", padx=8, pady=5)

                ctk.CTkLabel(
                    card,
                    text=f"{info['icon']}  {info['name']}  (Số lượng: {cnt})\nCông dụng: {info['effect']}",
                    font=("Segoe UI", 13, "bold"),
                    text_color="#FFFFFF",
                    justify="left",
                    wraplength=420
                ).pack(side="left", padx=14, pady=10)

                ctk.CTkButton(
                    card,
                    text="Sử dụng",
                    width=100,
                    height=34,
                    fg_color="#2D5A43",
                    hover_color="#3B7A57",
                    font=("Segoe UI", 13, "bold"),
                    command=lambda iid=item_id: use_it(iid)
                ).pack(side="right", padx=14, pady=10)

            if not has_any:
                ctk.CTkLabel(scroll, text="Túi đồ hiện đang trống. Hãy ghé Tàng Bảo Các để mua đan dược & pháp bảo!", font=("Segoe UI", 14)).pack(pady=30)

        def use_it(iid: str):
            info = VocabFarmEngine.SHOP_ITEMS[iid]
            if not messagebox.askyesno("Xác nhận sử dụng", f"Bạn có muốn sử dụng [{info['name']}] không?"):
                return
            res = self.farm_engine.dispatch("DUNG_VAT_PHAM", {"item_id": iid, "plot_id": self.selected_farm_plot_id})
            render_inv()
            self._refresh_farm_ui()
            if res.get("ok"):
                messagebox.showinfo("Túi Đồ", res.get("message", ""))
            else:
                messagebox.showwarning("Túi Đồ", res.get("message", ""))

        render_inv()

    def _open_pets_modal(self):
        win = ctk.CTkToplevel(self)
        win.title("🐾 Linh Thú Các")
        win.geometry("660x500")
        win.configure(fg_color="#183028")
        win.grab_set()

        ctk.CTkLabel(win, text="🐾 LINH THÚ ĐỒNG HÀNH", font=("Segoe UI", 19, "bold"), text_color="#FBBF24").pack(pady=(16, 10))
        scroll = ctk.CTkScrollableFrame(win, fg_color="#26463B", corner_radius=14)
        scroll.pack(fill="both", expand=True, padx=24, pady=(4, 18))

        def render_pets():
            state = self.farm_engine.get_state()
            owned = state.get("pets", {}).get("owned", {})
            active_id = state.get("pets", {}).get("active_pet", "")
            for w in scroll.winfo_children():
                w.destroy()

            for pid, pcfg in VocabFarmEngine.SPIRIT_PETS.items():
                is_owned = pid in owned
                lvl = owned.get(pid, {}).get("level", 1)
                is_active = (pid == active_id)

                card = ctk.CTkFrame(scroll, fg_color="#183028", corner_radius=12, border_width=2 if is_active else 0, border_color="#4ADE80")
                card.pack(fill="x", padx=8, pady=6)

                status_tag = " [ĐANG ĐỒNG HÀNH]" if is_active else (" [Đã sở hữu]" if is_owned else f" [Giá mở khóa: {pcfg['unlock_cost']} Linh Thạch]")
                ctk.CTkLabel(
                    card,
                    text=f"{pcfg['icon']}  {pcfg['name']} ({pcfg['rarity']}) — Cấp {lvl}{status_tag}\nKỹ năng: {pcfg['skill']}",
                    font=("Segoe UI", 13, "bold"),
                    text_color="#FFFFFF",
                    justify="left",
                    wraplength=410
                ).pack(side="left", padx=14, pady=12)

                btn_box = ctk.CTkFrame(card, fg_color="transparent")
                btn_box.pack(side="right", padx=12)

                act_txt = "Đang kích hoạt" if is_active else ("Kích hoạt" if is_owned else f"Thu phục ({pcfg['unlock_cost']} LT)")
                ctk.CTkButton(
                    btn_box,
                    text=act_txt,
                    width=130,
                    height=30,
                    state="disabled" if is_active else "normal",
                    fg_color="#2D5A43",
                    command=lambda p=pid: act_pet(p)
                ).pack(pady=2)

                if is_owned:
                    ctk.CTkButton(
                        btn_box,
                        text=f"Bồi dưỡng ({lvl*80} LT)",
                        width=130,
                        height=28,
                        fg_color="#9E7332",
                        command=lambda p=pid: upg_pet(p)
                    ).pack(pady=2)

        def act_pet(pid: str):
            res = self.farm_engine.dispatch("KICH_HOAT_LINH_THU", {"pet_id": pid})
            render_pets()
            self._refresh_farm_ui()
            messagebox.showinfo("Linh Thú", res.get("message", ""))

        def upg_pet(pid: str):
            res = self.farm_engine.dispatch("NANG_CAP_LINH_THU", {"pet_id": pid})
            render_pets()
            self._refresh_farm_ui()
            messagebox.showinfo("Linh Thú", res.get("message", ""))

        render_pets()

    def _open_quests_modal(self):
        win = ctk.CTkToplevel(self)
        win.title("📜 Bảng Nhiệm Vụ Tiên Gia")
        win.geometry("660x520")
        win.configure(fg_color="#183028")
        win.grab_set()

        ctk.CTkLabel(win, text="📜 BẢNG NHIỆM VỤ TU LUYỆN", font=("Segoe UI", 19, "bold"), text_color="#FBBF24").pack(pady=(16, 10))
        scroll = ctk.CTkScrollableFrame(win, fg_color="#26463B", corner_radius=14)
        scroll.pack(fill="both", expand=True, padx=24, pady=(4, 18))

        def render_quests():
            for w in scroll.winfo_children():
                w.destroy()
            quests = self.farm_engine.get_quests_status()
            for q in quests:
                card = ctk.CTkFrame(scroll, fg_color="#183028", corner_radius=12)
                card.pack(fill="x", padx=8, pady=6)

                info_txt = (
                    f"[{q['group']}] {q['title']} ({q['progress']}/{q['target']})\n"
                    f"{q['desc']}  •  Thưởng: +{q['reward_gold']} Linh Thạch, +{q['reward_tu_vi']} Tu Vi"
                )
                ctk.CTkLabel(card, text=info_txt, font=("Segoe UI", 13, "bold"), text_color="#FFFFFF", justify="left", wraplength=420).pack(side="left", padx=14, pady=12)

                if q["claimed"]:
                    btn_t, btn_st, btn_c = "Đã nhận", "disabled", "#475569"
                elif q["completed"]:
                    btn_t, btn_st, btn_c = "🎁 Nhận thưởng", "normal", "#D97706"
                else:
                    btn_t, btn_st, btn_c = "Chưa xong", "disabled", "#334155"

                ctk.CTkButton(
                    card,
                    text=btn_t,
                    state=btn_st,
                    fg_color=btn_c,
                    width=120,
                    height=34,
                    command=lambda qid=q["id"]: claim_q(qid)
                ).pack(side="right", padx=14, pady=10)

        def claim_q(qid: str):
            res = self.farm_engine.dispatch("NHAN_THUONG_NHIEM_VU", {"quest_id": qid})
            render_quests()
            self._refresh_farm_ui()
            messagebox.showinfo("Nhiệm Vụ", res.get("message", ""))

        render_quests()

    def _open_achievements_modal(self):
        state = self.farm_engine.get_state()
        unlocked = set(state.get("achievements_unlocked", []))
        stats = state.get("stats", {})

        win = ctk.CTkToplevel(self)
        win.title("🏆 Bảng Thành Tựu Tu Tiên")
        win.geometry("600x480")
        win.configure(fg_color="#183028")
        win.grab_set()

        ctk.CTkLabel(win, text="🏆 THÀNH TỰU ĐẠT ĐƯỢC", font=("Segoe UI", 19, "bold"), text_color="#FBBF24").pack(pady=(16, 10))
        scroll = ctk.CTkScrollableFrame(win, fg_color="#26463B", corner_radius=14)
        scroll.pack(fill="both", expand=True, padx=24, pady=(4, 18))

        ach_list = [
            ("first_harvest", "🌾 Lần đầu thu hoạch linh thảo", f"Đã thu hoạch: {stats.get('total_harvested', 0)}/1"),
            ("correct_100", "🎯 Đạt 100 câu trả lời đúng", f"Đã trả lời đúng: {stats.get('correct_answers', 0)}/100"),
            ("truc_co", "⚡ Đột phá cảnh giới Trúc Cơ", f"Cảnh giới hiện tại: {state.get('realm_name')}"),
            ("first_pet", "🐾 Sở hữu linh thú đầu tiên", "Đã kết khế ước với Thanh Lân Lộc"),
            ("realm_10", "⛰️ Hoàn thành 10 Bí Cảnh", f"Đã vượt qua: {stats.get('realms_cleared', 0)}/10"),
        ]
        for aid, title, sub in ach_list:
            done = aid in unlocked
            card = ctk.CTkFrame(scroll, fg_color="#183028", corner_radius=12, border_width=2 if done else 0, border_color="#FBBF24")
            card.pack(fill="x", padx=8, pady=5)
            badge = "✅ ĐÃ ĐẠT" if done else "🔒 Chưa mở"
            ctk.CTkLabel(card, text=f"{title}\n{sub}", font=("Segoe UI", 13, "bold"), text_color="#FFFFFF" if done else "#94A3B8", justify="left").pack(side="left", padx=14, pady=10)
            ctk.CTkLabel(card, text=badge, font=("Segoe UI", 13, "bold"), text_color="#4ADE80" if done else "#64748B").pack(side="right", padx=14)

    def _open_logs_modal(self):
        state = self.farm_engine.get_state()
        win = ctk.CTkToplevel(self)
        win.title("📖 Nhật Ký Linh Điền")
        win.geometry("640x460")
        win.configure(fg_color="#183028")
        win.grab_set()

        ctk.CTkLabel(win, text="📖 NHẬT KÝ HOẠT ĐỘNG LINH ĐIỀN", font=("Segoe UI", 18, "bold"), text_color="#FBBF24").pack(pady=(16, 8))
        txt = ctk.CTkTextbox(win, fg_color="#26463B", text_color="#F1F5F9", font=("Consolas", 13), wrap="word")
        txt.pack(fill="both", expand=True, padx=24, pady=(4, 18))
        logs = state.get("logs", [])
        txt.insert("1.0", "\n".join(logs) if logs else "Chưa có nhật ký hoạt động.")

    # =========================================================================
    # TRANG 7: CÀI ĐẶT HỆ THỐNG & KHÔI PHỤC MẶC ĐỊNH
    # =========================================================================
    def _build_settings_page(self):
        page = self.pages["settings"]
        page.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(page)
        card.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card, text="Cấu hình Hệ thống & Giao diện", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(20, 15))

        ctk.CTkLabel(card, text="Gemini API Key:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=20, pady=10)
        self.entry_api_key = ctk.CTkEntry(card, show="*", font=("Consolas", 13))
        self.entry_api_key.grid(row=1, column=1, sticky="ew", padx=10, pady=10)
        if Config.GEMINI_API_KEY:
            self.entry_api_key.insert(0, Config.GEMINI_API_KEY)

        self.show_key_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(card, text="Hiện Key", variable=self.show_key_var, command=self._toggle_api_key_visibility, width=80).grid(row=1, column=2, padx=20, pady=10)

        ctk.CTkLabel(card, text="Model cấu hình:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", padx=20, pady=10)
        self.settings_model_menu = ctk.CTkOptionMenu(card, values=Config.AVAILABLE_MODELS, width=240)
        self.settings_model_menu.set(Config.GEMINI_MODEL if Config.GEMINI_MODEL in Config.AVAILABLE_MODELS else "gemini-3.8-flash")
        self.settings_model_menu.grid(row=2, column=1, sticky="w", padx=10, pady=10)

        ctk.CTkLabel(card, text="Chế độ giao diện:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, sticky="w", padx=20, pady=10)
        self.settings_theme_menu = ctk.CTkOptionMenu(
            card,
            values=["Dark (Tối)", "Light (Sáng)", "System (Theo máy)"],
            width=240,
            command=self._change_theme
        )
        self.settings_theme_menu.grid(row=3, column=1, sticky="w", padx=10, pady=10)

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=4, column=0, columnspan=3, sticky="w", padx=20, pady=15)

        ctk.CTkButton(btn_row, text="💾 Lưu cấu hình", width=160, fg_color="#0D7A5F", hover_color="#095945", command=self._save_settings).pack(side="left", padx=(0, 8))
        self.btn_test_api = ctk.CTkButton(btn_row, text="🔌 Kiểm tra kết nối", width=180, command=self._test_api_from_ui)
        self.btn_test_api.pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="📂 Sao lưu Database (.db)", width=190, fg_color="#1F538D", command=self._backup_db_ui).pack(side="left", padx=8)

        reset_card = ctk.CTkFrame(page, border_width=1, border_color="#C0392B")
        reset_card.grid(row=1, column=0, sticky="ew", padx=10, pady=15)

        ctk.CTkLabel(
            reset_card,
            text="⚠️ Quản lý Dữ liệu & Khôi phục Mặc định",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#EF4444"
        ).pack(anchor="w", padx=20, pady=(15, 4))

        ctk.CTkLabel(
            reset_card,
            text="Chức năng này sẽ xóa sạch toàn bộ Từ vựng đã lưu, các Folder đã tạo, Lịch sử dịch, Lịch sử ngữ pháp và làm mới Linh Điền Ký.",
            font=ctk.CTkFont(size=13),
            text_color=("gray30", "gray70")
        ).pack(anchor="w", padx=20, pady=(0, 12))

        ctk.CTkButton(
            reset_card,
            text="🗑️ Xóa hết dữ liệu (Khôi phục về mặc định)",
            width=280,
            height=38,
            fg_color="#C0392B",
            hover_color="#962D22",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._reset_all_app_data
        ).pack(anchor="w", padx=20, pady=(0, 18))

        self.lbl_api_test_result = ctk.CTkLabel(card, text="", font=("Segoe UI", 13), justify="left")
        self.lbl_api_test_result.grid(row=5, column=0, columnspan=3, sticky="w", padx=20, pady=(5, 15))

    def _reset_all_app_data(self):
        if not messagebox.askyesno(
            "Xác nhận Khôi phục mặc định",
            "⚠️ Bạn có chắc chắn muốn XÓA HẾT DỮ LIỆU (Từ vựng, Folder, Lịch sử dịch, Lịch sử ngữ pháp, Linh Điền Ký) để khôi phục về mặc định không?"
        ):
            return

        keep_sample = messagebox.askyesno(
            "Tùy chọn từ vựng mẫu",
            "Bạn muốn giữ lại 11 từ mẫu của Folder 'Camvision' hay xóa trắng hoàn toàn (0 từ)?\n\n"
            "• Bấm YES: Giữ lại 11 từ mẫu Camvision.\n"
            "• Bấm NO: Xóa trắng hoàn toàn (0 từ)."
        )
        database.reset_all_data(keep_sample_camvision=keep_sample)
        self.farm_engine.reset_all_profiles()
        self.saved_page_index = 1
        self._sync_topic_menus(selected_topic="Camvision")
        self._refresh_saved_words()
        messagebox.showinfo("Hoàn tất", "Đã xóa sạch dữ liệu và khôi phục phần mềm về trạng thái mặc định!")

    def _toggle_api_key_visibility(self):
        self.entry_api_key.configure(show="" if self.show_key_var.get() else "*")

    def _change_theme(self, choice: str):
        if "Light" in choice:
            ctk.set_appearance_mode("Light")
        elif "Dark" in choice:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("System")

    def _save_settings(self):
        key = self.entry_api_key.get().strip()
        model = self.settings_model_menu.get().strip()
        Config.save_settings(key, model)
        self.status_lbl.configure(text=f"Model: {Config.GEMINI_MODEL}")
        messagebox.showinfo("Đã lưu", "Đã lưu cấu hình thành công!")

    def _test_api_from_ui(self):
        self.btn_test_api.configure(state="disabled", text="Đang kiểm tra...")
        self.lbl_api_test_result.configure(text="⏳ Đang kiểm tra kết nối...", text_color=("gray20", "gray80"))

        def worker():
            ok, msg = ai_service.test_api_connection()
            color = "#0D7A5F" if ok else "#C0392B"
            prefix = "✅ " if ok else "❌ "
            self.after(0, lambda: [
                self.lbl_api_test_result.configure(text=prefix + msg, text_color=color),
                self.btn_test_api.configure(state="normal", text="🔌 Kiểm tra kết nối")
            ])

        threading.Thread(target=worker, daemon=True).start()

    def _backup_db_ui(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db")],
            initialfile="backup_translator_pro.db"
        )
        if path:
            try:
                database.backup_database(path)
                messagebox.showinfo("Sao lưu thành công", f"Đã sao lưu an toàn toàn bộ dữ liệu ra file:\n{path}")
            except Exception as e:
                messagebox.showerror("Lỗi sao lưu", str(e))


if __name__ == "__main__":
    app = TranslatorProApp()
    app.mainloop()