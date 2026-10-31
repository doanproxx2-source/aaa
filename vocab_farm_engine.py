import json
import random
import time
from datetime import datetime
from pathlib import Path
import pypinyin

SAVE_FILE = Path(__file__).resolve().parent / "vocab_farm_saves.json"


class VocabFarmEngine:
    """
    Game Engine: LINH ĐIỀN KÝ – Tu Tiên Nông Trại.
    Tuân thủ tuyệt đối quy tắc: Tất cả câu hỏi Tưới nước, Kỳ Ngộ (Random Events)
    và Bí Cảnh đều lấy 100% từ vocab_pool của Folder người chơi đã chọn.
    """

    REALMS = [
        ("Luyện Khí Tầng 1", 200),
        ("Luyện Khí Tầng 2", 350),
        ("Luyện Khí Tầng 3", 500),
        ("Luyện Khí Tầng 4", 700),
        ("Luyện Khí Tầng 5", 950),
        ("Luyện Khí Tầng 6", 1250),
        ("Luyện Khí Tầng 7", 1600),
        ("Luyện Khí Tầng 8", 2000),
        ("Luyện Khí Tầng 9", 2500),
        ("Trúc Cơ Tầng 1", 3200),
        ("Trúc Cơ Tầng 2", 4000),
        ("Trúc Cơ Tầng 3", 5000),
        ("Kim Đan Tầng 1", 6500),
        ("Nguyên Anh Tầng 1", 9000),
        ("Hóa Thần Tầng 1", 15000),
    ]

    SHOP_ITEMS = {
        "tra_sua": {
            "name": "Hồi Linh Đan",
            "icon": "💊",
            "category": "Đan dược",
            "price": 15,
            "desc": "Đan dược chưng cất từ linh thảo trăm năm.",
            "effect": "Hồi đầy 200 / 200 Linh Khí ngay lập tức"
        },
        "tay_tuy_dan": {
            "name": "Tẩy Tủy Đan",
            "icon": "🔮",
            "category": "Đan dược",
            "price": 40,
            "desc": "Đan dược tẩy luyện kinh mạch, tăng mạnh tu vi.",
            "effect": "Tăng trực tiếp +120 Tu Vi"
        },
        "thuoc_tru_sau": {
            "name": "Bùa May Mắn",
            "icon": "📜",
            "category": "Pháp bảo",
            "price": 20,
            "desc": "Linh phù tụ khí giúp linh thảo tự lớn không cần khảo nghiệm.",
            "effect": "Bỏ qua Quiz, tăng +1 Growth cho ô đất đang chọn"
        },
        "phan_bon": {
            "name": "Tiên Lộ Linh Dịch",
            "icon": "🧪",
            "category": "Nguyên liệu",
            "price": 50,
            "desc": "Nước sương sớm tích tụ linh khí đất trời.",
            "effect": "Tăng vọt +2 Growth cho cây trên ô đất đang chọn"
        },
        "hat_vip": {
            "name": "Hạt Giống Tiên Phẩm",
            "icon": "🌟",
            "category": "Nguyên liệu",
            "price": 100,
            "desc": "Nâng cấp linh thảo hiện tại lên phẩm chất Tiên Phẩm.",
            "effect": "Khi thu hoạch nhận 150 Linh Thạch & +80 Tu Vi"
        },
        "binh_nuoc": {
            "name": "Tịnh Thủy Phù",
            "icon": "💧",
            "category": "Pháp bảo",
            "price": 20,
            "desc": "Phù chú thanh tẩy tà khí khiến cây bị héo.",
            "effect": "Xóa bỏ hoàn toàn thời gian Cooldown của ô đất"
        },
        "mo_o_dat": {
            "name": "Khai Hoang Lệnh",
            "icon": "🟫",
            "category": "Pháp bảo",
            "price": 100,
            "desc": "Lệnh bài mở rộng ranh giới linh điền.",
            "effect": "Mở thêm +1 ô đất mới trên Linh Điền"
        }
    }

    SPIRIT_PETS = {
        "thanh_lan_loc": {
            "id": "thanh_lan_loc",
            "name": "Thanh Lân Lộc",
            "icon": "🦌",
            "rarity": "Linh Phẩm",
            "skill": "Tưới nước đúng nhận thêm +10 Tu Vi",
            "tu_vi_bonus": 10,
            "gold_bonus": 0,
            "unlock_cost": 0
        },
        "huyen_hoa_ho": {
            "id": "huyen_hoa_ho",
            "name": "Huyền Hỏa Hồ",
            "icon": "🦊",
            "rarity": "Địa Phẩm",
            "skill": "Thu hoạch linh thảo nhận thêm +25 Linh Thạch",
            "tu_vi_bonus": 5,
            "gold_bonus": 25,
            "unlock_cost": 200
        },
        "thai_hu_long": {
            "id": "thai_hu_long",
            "name": "Thái Hư Thanh Long",
            "icon": "🐉",
            "rarity": "Tiên Phẩm",
            "skill": "Tưới nước +20 Tu Vi & Thu hoạch +50 Linh Thạch",
            "tu_vi_bonus": 20,
            "gold_bonus": 50,
            "unlock_cost": 500
        }
    }

    SECRET_REALMS = [
        {
            "id": "thanh_van",
            "name": "Thanh Vân Bí Cảnh",
            "difficulty": "Dễ",
            "diff_color": "#DCFCE7",
            "diff_text_color": "#15803D",
            "req_realm_idx": 0,
            "req_realm_name": "Luyện Khí",
            "areas_count": 5,
            "boss_name": "Thanh Vân Linh Xà",
            "boss_hp": 60,
            "reward_gold": 100,
            "reward_tu_vi": 100,
            "reward_item": None,
            "reward_desc": "Thưởng: +100 Linh Thạch, +100 Tu Vi",
            "desc": "Một khu rừng cổ chứa nhiều linh thảo và bảo vật.",
            "stages": [
                {"name": "Khu vực 1 – Cổng Bí Cảnh", "type": "gate", "q_type": "zh_to_vi", "hp_pen": 10, "story": "Bạn đứng trước cánh cổng đá cổ phong ấn bằng cổ ngữ."},
                {"name": "Khu vực 2 – Linh Thảo Viên", "type": "herb", "q_type": "zh_to_py", "hp_pen": 10, "story": "Một vườn linh thảo tỏa hương thơm ngát, cần nhận diện đúng âm đọc để hái."},
                {"name": "Khu vực 3 – Mê Vụ Trận", "type": "trap", "q_type": "fill_blank", "hp_pen": 15, "story": "Sương mù dày đặc che khuất lối đi, các ký tự Hán ngữ ẩn hiện trong trận pháp."},
                {"name": "Khu vực 4 – Yêu Thú Thủ Hộ", "type": "monster", "q_type": "vi_to_zh", "hp_pen": 20, "story": "Yêu thú canh giữ lối vào sào huyệt xuất hiện ngăn cản bạn."},
                {"name": "Khu vực 5 – Bí Cảnh Chi Chủ", "type": "boss", "q_type": "mix", "hp_pen": 20, "story": "Thanh Vân Linh Xà xuất hiện! Hãy dùng kiến thức Hán ngữ để đánh bại nó!"}
            ]
        },
        {
            "id": "u_minh",
            "name": "U Minh Cổ Điện",
            "difficulty": "Trung bình",
            "diff_color": "#FFEDD5",
            "diff_text_color": "#C2410C",
            "req_realm_idx": 9,
            "req_realm_name": "Trúc Cơ",
            "areas_count": 7,
            "boss_name": "U Minh Quỷ Tướng",
            "boss_hp": 90,
            "reward_gold": 250,
            "reward_tu_vi": 200,
            "reward_item": "tra_sua",
            "reward_desc": "Thưởng: +250 Linh Thạch, +200 Tu Vi, Đan dược",
            "desc": "Cổ điện bị phong ấn, ẩn chứa nhiều bí mật.",
            "stages": [
                {"name": "Khu vực 1 – Điện Môn Phong Ấn", "type": "gate", "q_type": "zh_to_vi", "hp_pen": 10, "story": "Cánh cửa đồng xanh khắc đầy minh văn cổ đại."},
                {"name": "Khu vực 2 – Hành Lang U Ám", "type": "trap", "q_type": "zh_to_py", "hp_pen": 15, "story": "Đèn lồng xanh lập lòe, âm thanh vọng lại thử thách thính giác của bạn."},
                {"name": "Khu vực 3 – Bảo Rương Cổ Điện", "type": "chest", "q_type": "vi_to_zh", "hp_pen": 10, "story": "Một chiếc rương sắt nằm khuất sau bức tượng cổ."},
                {"name": "Khu vực 4 – Hắc Ám Trận Pháp", "type": "trap", "q_type": "fill_blank", "hp_pen": 15, "story": "Trận pháp phát sáng, yêu cầu điền đúng từ khóa để mở lối."},
                {"name": "Khu vực 5 – Âm Binh Canh Gác", "type": "monster", "q_type": "zh_to_vi", "hp_pen": 20, "story": "Chiến binh cổ đại thức tỉnh, vung trường kích ngăn đường."},
                {"name": "Khu vực 6 – Mật Thất Đan Dược", "type": "herb", "q_type": "vi_to_zh", "hp_pen": 15, "story": "Mật thất lưu giữ các bình đan dược từ thời thượng cổ."},
                {"name": "Khu vực 7 – Bí Cảnh Chi Chủ", "type": "boss", "q_type": "mix", "hp_pen": 20, "story": "U Minh Quỷ Tướng thức giấc! Đánh bại hắn để làm chủ cổ điện!"}
            ]
        },
        {
            "id": "cuu_u",
            "name": "Cửu U Tuyệt Địa",
            "difficulty": "Khó",
            "diff_color": "#FEE2E2",
            "diff_text_color": "#B91C1C",
            "req_realm_idx": 12,
            "req_realm_name": "Kim Đan",
            "areas_count": 10,
            "boss_name": "Cửu U Ma Chủ",
            "boss_hp": 120,
            "reward_gold": 500,
            "reward_tu_vi": 400,
            "reward_item": "tay_tuy_dan",
            "reward_desc": "Thưởng: +500 Linh Thạch, +400 Tu Vi, Bảo vật hiếm",
            "desc": "Vùng đất nguy hiểm với nhiều yêu thú mạnh.",
            "stages": [
                {"name": "Khu vực 1 – Vực Thẳm Cửu U", "type": "gate", "q_type": "zh_to_vi", "hp_pen": 10, "story": "Dung nham nóng rực cuộn trào dưới chân núi đá đen."},
                {"name": "Khu vực 2 – Hỏa Diễm Trận", "type": "trap", "q_type": "zh_to_py", "hp_pen": 15, "story": "Ngọn lửa ma quái hóa thành những ký tự phiên âm biến ảo."},
                {"name": "Khu vực 3 – Huyết Tinh Bảo Rương", "type": "chest", "q_type": "vi_to_zh", "hp_pen": 15, "story": "Rương báu nằm giữa vòng vây sát khí."},
                {"name": "Khu vực 4 – Yêu Thú Tuyệt Địa", "type": "monster", "q_type": "fill_blank", "hp_pen": 20, "story": "Yêu thú khổng lồ gầm vang làm rung chuyển cả vùng đất."},
                {"name": "Khu vực 5 – Tâm Ma Ảo Cảnh", "type": "trap", "q_type": "zh_to_py", "hp_pen": 15, "story": "Ảo ảnh tâm ma xâm nhập tâm trí, hãy giữ vững đạo tâm!"},
                {"name": "Khu vực 6 – Cổ Bia Minh Văn", "type": "gate", "q_type": "fill_blank", "hp_pen": 15, "story": "Tấm bia đá cổ ghi lại khẩu quyết vượt qua vùng tuyệt địa."},
                {"name": "Khu vực 7 – Vườn Thiên Tài Địa Bảo", "type": "herb", "q_type": "vi_to_zh", "hp_pen": 15, "story": "Những gốc linh thảo ngàn năm mọc trên vách đá hiểm trở."},
                {"name": "Khu vực 8 – Hộ Pháp Ma Tướng", "type": "monster", "q_type": "zh_to_vi", "hp_pen": 20, "story": "Hộ pháp dưới trướng Ma Chủ chặn đứng đường tiến của bạn."},
                {"name": "Khu vực 9 – Cửu U Phong Ấn", "type": "trap", "q_type": "fill_blank", "hp_pen": 20, "story": "Lớp phong ấn cuối cùng trước điện chính của Ma Chủ."},
                {"name": "Khu vực 10 – Bí Cảnh Chi Chủ", "type": "boss", "q_type": "mix", "hp_pen": 20, "story": "Cửu U Ma Chủ giáng lâm! Vượt qua thử thách cuối cùng để vang danh thiên hạ!"}
            ]
        }
    ]

    def __init__(self):
        self.profiles = {}
        self.current_profile = "Đoàn Đặng Quang"
        self.load_all_profiles()

    def load_all_profiles(self):
        if SAVE_FILE.exists():
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.profiles = data.get("profiles", {})
                    self.current_profile = data.get("current_profile", "Đoàn Đặng Quang")
            except Exception:
                self.profiles = {}
        if self.current_profile not in self.profiles:
            self._create_default_profile(self.current_profile)
        else:
            self._ensure_cultivation_fields(self.profiles[self.current_profile])

    def reset_all_profiles(self):
        self.profiles = {}
        self.current_profile = "Đoàn Đặng Quang"
        self._create_default_profile(self.current_profile)
        self._save_to_disk()

    def _create_default_profile(self, profile_name: str):
        self.profiles[profile_name] = {
            "profile_name": profile_name,
            "realm_idx": 2,
            "tu_vi": 320,
            "max_tu_vi": 500,
            "breakthrough_count": 2,
            "gold": 1250,
            "energy": 180,
            "max_energy": 200,
            "last_energy_tick": time.time(),
            "folder_name": "Camvision",
            "total_plots": 9,
            "land_expand_count": 0,
            "timer_enabled": False,
            "time_limit": 45,
            "waters_since_last_event": 0,
            "recent_words": [],
            "wrong_words": {},
            "inventory": {
                "tra_sua": 2,
                "tay_tuy_dan": 1,
                "thuoc_tru_sau": 2,
                "phan_bon": 1,
                "hat_vip": 1,
                "binh_nuoc": 2
            },
            "pets": {
                "active_pet": "thanh_lan_loc",
                "owned": {
                    "thanh_lan_loc": {"level": 1, "exp": 0}
                }
            },
            "stats": {
                "total_harvested": 0,
                "correct_answers": 0,
                "water_count": 0,
                "realms_cleared": 0
            },
            "quests_claimed": [],
            "achievements_unlocked": [],
            "logs": [
                f"[{datetime.now().strftime('%H:%M:%S')}] Bước chân vào Linh Điền Ký – Khởi đầu tu luyện!"
            ],
            "random_event": None,
            "plots": {},
            "seed_queue": [],
            "vocab_pool": []
        }

    def _ensure_cultivation_fields(self, state: dict):
        defaults = {
            "realm_idx": 2,
            "tu_vi": 320,
            "max_tu_vi": 500,
            "breakthrough_count": 2,
            "waters_since_last_event": 0,
            "recent_words": [],
            "wrong_words": {},
            "pets": {"active_pet": "thanh_lan_loc", "owned": {"thanh_lan_loc": {"level": 1, "exp": 0}}},
            "stats": {"total_harvested": 0, "correct_answers": 0, "water_count": 0, "realms_cleared": 0},
            "quests_claimed": [],
            "achievements_unlocked": [],
            "logs": [],
            "random_event": None
        }
        for k, v in defaults.items():
            if k not in state:
                state[k] = v
        inv = state.setdefault("inventory", {})
        inv.setdefault("tay_tuy_dan", 1)

    def _add_log(self, text: str):
        state = self.profiles[self.current_profile]
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logs = state.setdefault("logs", [])
        logs.insert(0, f"[{stamp}] {text}")
        if len(logs) > 100:
            state["logs"] = logs[:100]

    def _check_achievements(self):
        state = self.profiles[self.current_profile]
        unlocked = set(state.get("achievements_unlocked", []))
        stats = state.get("stats", {})

        rules = [
            ("first_harvest", "Lần đầu thu hoạch linh thảo", stats.get("total_harvested", 0) >= 1),
            ("correct_100", "Đạt 100 câu trả lời đúng", stats.get("correct_answers", 0) >= 100),
            ("truc_co", "Đột phá cảnh giới Trúc Cơ", state.get("realm_idx", 0) >= 9),
            ("first_pet", "Sở hữu linh thú đầu tiên", len(state.get("pets", {}).get("owned", {})) >= 1),
            ("realm_10", "Hoàn thành 10 lần Bí Cảnh", stats.get("realms_cleared", 0) >= 10),
        ]
        for ach_id, title, cond in rules:
            if cond and ach_id not in unlocked:
                unlocked.add(ach_id)
                self._add_log(f"🏆 Mở khóa Thành Tựu: {title}!")
        state["achievements_unlocked"] = list(unlocked)

    def get_state(self) -> dict:
        self._update_passive_energy()
        state = self.profiles[self.current_profile]
        self._ensure_cultivation_fields(state)
        idx = min(state.get("realm_idx", 0), len(self.REALMS) - 1)
        state["realm_name"] = self.REALMS[idx][0]
        state["max_tu_vi"] = self.REALMS[idx][1]
        self._check_achievements()
        return state

    def _update_passive_energy(self):
        state = self.profiles[self.current_profile]
        now = time.time()
        elapsed = now - state.get("last_energy_tick", now)
        if elapsed >= 10:
            ticks = int(elapsed // 10)
            if state["energy"] < state["max_energy"]:
                state["energy"] = min(state["max_energy"], state["energy"] + ticks)
            state["last_energy_tick"] = now - (elapsed % 10)

    def sync_vocab_pool(self, folder_name: str, vocab_pool: list):
        """Đồng bộ danh sách từ vựng của Folder đang chọn vào Game Engine."""
        state = self.profiles[self.current_profile]
        state["folder_name"] = folder_name
        state["vocab_pool"] = vocab_pool

    # =========================================================================
    # BỘ SINH CÂU HỎI ĐỘNG 100% TỪ VOCAB_POOL CỦA THƯ MỤC ĐANG CHỌN
    # =========================================================================
    @staticmethod
    def _to_pinyin(text: str) -> str:
        if not text:
            return ""
        res = pypinyin.pinyin(text, style=pypinyin.Style.TONE)
        return " ".join([item[0] for item in res])

    def _pick_smart_word_from_pool(self, pool: list, exclude_words: set = None) -> dict:
        """
        Chọn từ ngẫu nhiên trong vocab_pool:
        - Không lấy từ ngoài thư mục.
        - Hạn chế lặp lại từ vừa hỏi.
        - Tăng xác suất những từ người chơi từng trả lời sai.
        """
        state = self.profiles[self.current_profile]
        exclude_words = exclude_words or set()
        recent = set(state.get("recent_words", [])[-5:])
        wrong_map = state.get("wrong_words", {})

        candidates = [w for w in pool if w.get("word") not in exclude_words]
        if not candidates:
            candidates = list(pool)

        non_recent = [w for w in candidates if w.get("word") not in recent]
        if non_recent:
            candidates = non_recent

        weighted_list = []
        for w in candidates:
            w_zh = w.get("word", "")
            weight = 1 + min(4, wrong_map.get(w_zh, 0) * 2)
            weighted_list.extend([w] * weight)

        chosen = random.choice(weighted_list) if weighted_list else random.choice(pool)

        recent_list = state.setdefault("recent_words", [])
        recent_list.append(chosen.get("word", ""))
        if len(recent_list) > 15:
            state["recent_words"] = recent_list[-15:]

        return chosen

    def build_pool_question(self, pool: list, q_type: str = "auto", target_word_data: dict = None, exclude_words: set = None) -> dict:
        """
        Tạo câu hỏi trắc nghiệm 4 đáp án A, B, C, D hoàn toàn từ vocab_pool của Folder hiện tại.
        Đáp án sai cũng lấy 100% từ các từ khác trong chính vocab_pool.
        """
        if not pool or len(pool) < 4:
            return {
                "error": True,
                "message": f"Thư mục hiện tại chỉ có {len(pool) if pool else 0} từ vựng (Cần tối thiểu 4 từ để tạo 4 đáp án A, B, C, D). Vui lòng thêm từ hoặc chọn thư mục khác!"
            }

        target = target_word_data or self._pick_smart_word_from_pool(pool, exclude_words=exclude_words)
        w_zh = target.get("word", "").strip()
        w_py = (target.get("pinyin") or self._to_pinyin(w_zh)).strip()
        w_hv = (target.get("hanviet") or "").strip().upper()
        w_vi = (target.get("meaning") or "").split("|")[0].strip()
        ex_zh = (target.get("example_zh") or "").strip()
        ex_vi = (target.get("example_vi") or "").strip()

        other_items = [item for item in pool if item.get("word", "").strip() != w_zh]

        if q_type == "auto":
            q_type = random.choices(["zh_to_vi", "vi_to_zh", "zh_to_py", "fill_blank"], weights=[40, 25, 20, 15])[0]

        if q_type == "fill_blank" and (not ex_zh or w_zh not in ex_zh):
            q_type = "zh_to_vi"

        # Dạng 1: Chọn nghĩa tiếng Việt của từ tiếng Trung
        if q_type == "zh_to_vi":
            distractor_vis = []
            for item in other_items:
                m = (item.get("meaning") or "").split("|")[0].strip()
                if m and m != w_vi and m not in distractor_vis:
                    distractor_vis.append(m)
            chosen_distractors = random.sample(distractor_vis, min(3, len(distractor_vis)))
            while len(chosen_distractors) < 3:
                chosen_distractors.append(f"Nghĩa khác #{len(chosen_distractors)+1}")

            raw_options = chosen_distractors + [w_vi]
            random.shuffle(raw_options)
            correct_val = w_vi
            prompt_title = f"Từ vựng “{w_zh}” có nghĩa tiếng Việt là gì?"
            sub_instruction = f"Hán Việt: {w_hv or 'N/A'}  •  Hãy chọn nghĩa tiếng Việt chính xác."

        # Dạng 2: Chọn chữ Hán tương ứng với nghĩa tiếng Việt
        elif q_type == "vi_to_zh":
            distractor_zhs = []
            for item in other_items:
                z = item.get("word", "").strip()
                if z and z != w_zh and z not in distractor_zhs:
                    distractor_zhs.append(z)
            chosen_distractors = random.sample(distractor_zhs, min(3, len(distractor_zhs)))

            raw_options = chosen_distractors + [w_zh]
            random.shuffle(raw_options)
            correct_val = w_zh
            prompt_title = f"Từ tiếng Trung nào có nghĩa là:\n“{w_vi}” ?"
            sub_instruction = f"Hán Việt gợi ý: {w_hv or 'N/A'}  •  Hãy chọn chữ Hán chính xác."

        # Dạng 3: Chọn Pinyin đúng (Đáp án sai lấy từ Pinyin của những từ khác trong vocab_pool)
        elif q_type == "zh_to_py":
            distractor_pys = []
            for item in other_items:
                p = (item.get("pinyin") or self._to_pinyin(item.get("word", ""))).strip()
                if p and p != w_py and p not in distractor_pys:
                    distractor_pys.append(p)
            chosen_distractors = random.sample(distractor_pys, min(3, len(distractor_pys)))
            while len(chosen_distractors) < 3:
                chosen_distractors.append(w_py + "~")

            raw_options = chosen_distractors + [w_py]
            random.shuffle(raw_options)
            correct_val = w_py
            prompt_title = f"Pinyin chính xác của từ “{w_zh}” là gì?"
            sub_instruction = f"Nghĩa: {w_vi} ({w_hv or 'N/A'})  •  Hãy chọn phiên âm Pinyin đúng."

        # Dạng 4: Điền từ còn thiếu vào câu ví dụ trong vocab_pool
        else:
            masked_zh = ex_zh.replace(w_zh, " ______ ")
            distractor_zhs = [item.get("word", "").strip() for item in other_items if item.get("word", "").strip() != w_zh]
            chosen_distractors = random.sample(distractor_zhs, min(3, len(distractor_zhs)))

            raw_options = chosen_distractors + [w_zh]
            random.shuffle(raw_options)
            correct_val = w_zh
            prompt_title = f"Điền từ thích hợp vào chỗ trống:\n{masked_zh}"
            sub_instruction = f"Nghĩa câu: “{ex_vi}”" if ex_vi else f"Từ cần điền mang nghĩa: “{w_vi}”"

        explanation = f"• Từ vựng: {w_zh} [{w_py}]\n• Âm Hán Việt: {w_hv or 'N/A'}\n• Nghĩa: {w_vi}"
        if ex_zh:
            explanation += f"\n• Ví dụ: {ex_zh} ({ex_vi})"

        return {
            "error": False,
            "word": w_zh,
            "pinyin": w_py,
            "hanviet": w_hv,
            "meaning": w_vi,
            "q_type": q_type,
            "prompt_title": prompt_title,
            "sub_instruction": sub_instruction,
            "options": raw_options,
            "correct_answer": correct_val,
            "explanation": explanation
        }

    def _generate_random_event_from_pool(self, pool: list) -> dict:
        """
        Sinh Sự kiện Ngẫu nhiên (Kỳ Ngộ) sử dụng 100% từ vựng trong vocab_pool của thư mục đang chọn.
        """
        if not pool or len(pool) < 4:
            return None

        state = self.profiles[self.current_profile]
        folder_name = state.get("folder_name", "Camvision")

        event_templates = [
            {
                "code": "KY_NGO",
                "weight": 30,
                "icon": "🎁",
                "title": "KỲ NGỘ – Phát hiện bảo rương",
                "story": f"Bạn đang tưới linh điền thì phát hiện một chiếc rương cổ khắc ký tự thuộc thư mục 【{folder_name}】. Giải được câu đố mới có thể mở ra.",
                "q_types": ["zh_to_vi", "vi_to_zh", "zh_to_py"],
                "q_weights": [60, 20, 20],
                "reward_text": "+100 Linh Thạch",
                "reward_gold": 100,
                "reward_tu_vi": 0,
                "reward_energy": 0,
                "penalty_energy": 0
            },
            {
                "code": "YEU_THU",
                "weight": 25,
                "icon": "🐺",
                "title": "YÊU THÚ TẤN CÔNG",
                "story": f"Một con yêu thú bị thu hút bởi linh khí quanh linh điền và lao tới tấn công! Hãy vận dụng từ vựng 【{folder_name}】 để đánh đuổi nó.",
                "q_types": ["vi_to_zh", "zh_to_vi", "zh_to_py"],
                "q_weights": [50, 30, 20],
                "reward_text": "+20 Linh Khí (Sai: -20 Linh Khí)",
                "reward_gold": 0,
                "reward_tu_vi": 20,
                "reward_energy": 20,
                "penalty_energy": 20
            },
            {
                "code": "TAM_MA",
                "weight": 20,
                "icon": "🔮",
                "title": "TÂM MA – Ảo Cảnh",
                "story": "Sương mù tím đậm bao phủ, các ký tự tiếng Trung liên tục biến ảo. Hãy nhận diện đúng Pinyin để phá tan ảo cảnh!",
                "q_types": ["zh_to_py"],
                "q_weights": [100],
                "reward_text": "+50 Tu Vi (Sai: -10 Linh Khí)",
                "reward_gold": 0,
                "reward_tu_vi": 50,
                "reward_energy": 0,
                "penalty_energy": 10
            },
            {
                "code": "THUONG_NHAN",
                "weight": 13,
                "icon": "🏮",
                "title": "THƯƠNG NHÂN BÍ ẨN",
                "story": "Một thương nhân mặc áo choàng ghé qua linh điền. Nếu vượt qua câu hỏi khảo nghiệm, ông ta sẽ nhượng lại đan dược với giá ưu đãi!",
                "q_types": ["fill_blank", "vi_to_zh", "zh_to_vi"],
                "q_weights": [50, 25, 25],
                "reward_text": "Mở Cửa Hàng Ưu Đãi Giảm 50% + 50 Linh Thạch",
                "reward_gold": 50,
                "reward_tu_vi": 0,
                "reward_energy": 0,
                "penalty_energy": 0
            },
            {
                "code": "TIEN_NHAN",
                "weight": 5,
                "icon": "🧙‍♂️",
                "title": "KỲ NGỘ HIẾM – Tiên Nhân Chỉ Điểm",
                "story": "Một vị lão tiên nhân cưỡi hạc đi ngang qua, mỉm cười khảo nghiệm đạo hạnh Hán ngữ của bạn.",
                "q_types": ["zh_to_vi", "zh_to_py"],
                "q_weights": [50, 50],
                "reward_text": "+100 Tu Vi",
                "reward_gold": 0,
                "reward_tu_vi": 100,
                "reward_energy": 0,
                "penalty_energy": 0
            },
            {
                "code": "LINH_KHI",
                "weight": 4,
                "icon": "✨",
                "title": "KỲ NGỘ HIẾM – Linh Khí Bùng Nổ",
                "story": "Mạch linh tuyền dưới lòng đất bất ngờ phun trào một luồng linh khí tinh thuần!",
                "q_types": ["vi_to_zh", "zh_to_vi"],
                "q_weights": [50, 50],
                "reward_text": "+50 Linh Khí",
                "reward_gold": 0,
                "reward_tu_vi": 0,
                "reward_energy": 50,
                "penalty_energy": 0
            },
            {
                "code": "THIEN_TAI",
                "weight": 3,
                "icon": "🌟",
                "title": "KỲ NGỘ HIẾM – Thiên Tài Địa Bảo",
                "story": "Ánh hào quang lóe lên ở góc linh điền, lộ ra một món bảo vật tiên gia hiếm có!",
                "q_types": ["zh_to_vi", "vi_to_zh"],
                "q_weights": [50, 50],
                "reward_text": "Nhận 1 Pháp Bảo / Đan Dược ngẫu nhiên",
                "reward_gold": 0,
                "reward_tu_vi": 30,
                "reward_energy": 0,
                "penalty_energy": 0,
                "bonus_item": random.choice(["tra_sua", "tay_tuy_dan", "thuoc_tru_sau", "phan_bon", "binh_nuoc"])
            }
        ]

        tpl = random.choices(event_templates, weights=[t["weight"] for t in event_templates])[0]
        chosen_q_type = random.choices(tpl["q_types"], weights=tpl["q_weights"])[0]
        q_data = self.build_pool_question(pool, q_type=chosen_q_type)
        if q_data.get("error"):
            return None

        return {
            "code": tpl["code"],
            "icon": tpl["icon"],
            "title": tpl["title"],
            "story": tpl["story"],
            "word": q_data["word"],
            "prompt_title": q_data["prompt_title"],
            "sub_instruction": q_data["sub_instruction"],
            "options": q_data["options"],
            "correct": q_data["correct_answer"],
            "explanation": q_data["explanation"],
            "reward_text": tpl["reward_text"],
            "reward_gold": tpl["reward_gold"],
            "reward_tu_vi": tpl["reward_tu_vi"],
            "reward_energy": tpl["reward_energy"],
            "penalty_energy": tpl["penalty_energy"],
            "bonus_item": tpl.get("bonus_item")
        }

    def dispatch(self, action: str, payload: dict = None) -> dict:
        payload = payload or {}
        self._update_passive_energy()
        state = self.profiles[self.current_profile]
        self._ensure_cultivation_fields(state)

        if action == "KHOI_TAO_GAME":
            res = self._action_init_game(payload)
        elif action == "MUA_HANG":
            res = self._action_buy_item(payload)
        elif action == "GIEO_HAT":
            res = self._action_plant_seed(payload)
        elif action == "TUOI_NUOC":
            res = self._action_water_plant(payload)
        elif action == "TRA_LOI_QUIZ":
            res = self._action_answer_quiz(payload)
        elif action == "THU_HOACH":
            res = self._action_harvest(payload)
        elif action == "DUNG_VAT_PHAM":
            res = self._action_use_item(payload)
        elif action == "DOT_PHA":
            res = self._action_breakthrough(payload)
        elif action == "GIAI_QUYET_SU_KIEN":
            res = self._action_resolve_event(payload)
        elif action == "KICH_HOAT_LINH_THU":
            res = self._action_activate_pet(payload)
        elif action == "NANG_CAP_LINH_THU":
            res = self._action_upgrade_pet(payload)
        elif action == "NHAN_THUONG_NHIEM_VU":
            res = self._action_claim_quest(payload)
        elif action == "HOAN_THANH_BI_CANH":
            res = self._action_complete_secret_realm(payload)
        elif action == "LUU_GAME":
            res = self._save_to_disk()
        else:
            res = {"ok": False, "message": f"Action không hợp lệ: {action}"}

        if action != "LUU_GAME":
            self._save_to_disk()
        return res

    def _save_to_disk(self) -> dict:
        data = {
            "current_profile": self.current_profile,
            "profiles": self.profiles
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"ok": True, "state": self.profiles[self.current_profile]}

    def _action_init_game(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        folder_name = payload.get("folder_name", "Camvision")
        vocab_pool = payload.get("vocab_pool", [])
        total_plots = int(payload.get("total_plots", state.get("total_plots", 9)))

        state["folder_name"] = folder_name
        state["total_plots"] = total_plots
        state["vocab_pool"] = vocab_pool
        state["random_event"] = None

        shuffled = list(vocab_pool)
        random.shuffle(shuffled)

        plots = {}
        for i in range(total_plots):
            plot_id = str(i)
            if i < len(shuffled):
                w_item = shuffled[i]
                init_growth = 1 if i % 3 == 0 else (2 if i % 3 == 1 else 0)
                plots[plot_id] = {
                    "plot_id": plot_id,
                    "word_data": w_item,
                    "growth": init_growth,
                    "is_vip": False,
                    "withered": False,
                    "cooldown_until": 0
                }
            else:
                plots[plot_id] = {
                    "plot_id": plot_id,
                    "word_data": None,
                    "growth": 0,
                    "is_vip": False,
                    "withered": False,
                    "cooldown_until": 0
                }

        state["plots"] = plots
        state["seed_queue"] = shuffled[total_plots:]
        self._add_log(f"Gieo hạt Linh Điền [{folder_name}] trên {total_plots} ô đất.")
        return {
            "ok": True,
            "message": f"🌱 Đã khai mở Linh Điền [{folder_name}] ({total_plots} ô đất)!"
        }

    def _action_buy_item(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        item_id = payload.get("item_id")
        discount = float(payload.get("discount", 1.0))
        if item_id not in self.SHOP_ITEMS:
            return {"ok": False, "message": "Pháp bảo/Đan dược không tồn tại!"}

        item_info = self.SHOP_ITEMS[item_id]
        base_price = item_info["price"]
        if item_id == "mo_o_dat":
            base_price = 100 * (state.get("land_expand_count", 0) + 1)
        price = max(1, int(base_price * discount))

        if state["gold"] < price:
            return {"ok": False, "message": f"Không đủ Linh Thạch! Cần {price} Linh Thạch nhưng bạn hiện có {state['gold']}."}

        state["gold"] -= price

        if item_id == "mo_o_dat":
            new_plot_id = str(state["total_plots"])
            state["total_plots"] += 1
            state["land_expand_count"] = state.get("land_expand_count", 0) + 1
            next_word = state["seed_queue"].pop(0) if state["seed_queue"] else None
            state["plots"][new_plot_id] = {
                "plot_id": new_plot_id,
                "word_data": next_word,
                "growth": 0,
                "is_vip": False,
                "withered": False,
                "cooldown_until": 0
            }
            self._add_log(f"Dùng {price} Linh Thạch mua Khai Hoang Lệnh, mở ô đất #{int(new_plot_id)+1}.")
            return {"ok": True, "message": f"🟫 Đã khai mở thêm Ô đất #{int(new_plot_id)+1}!"}
        else:
            state["inventory"][item_id] = state["inventory"].get(item_id, 0) + 1
            self._add_log(f"Mua {item_info['name']} (-{price} Linh Thạch).")
            return {"ok": True, "message": f"Đã mua [{item_info['name']}] đưa vào Túi Đồ!"}

    def _action_plant_seed(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        plot_id = str(payload.get("plot_id"))
        word_data = payload.get("word")
        plot = state["plots"].get(plot_id)
        if not plot:
            return {"ok": False, "message": "Ô đất không hợp lệ!"}
        if plot.get("word_data"):
            return {"ok": False, "message": "Ô đất này đang có linh thảo rồi!"}

        if not word_data and state["seed_queue"]:
            word_data = state["seed_queue"].pop(0)
        elif not word_data and state["vocab_pool"]:
            word_data = random.choice(state["vocab_pool"])

        if not word_data:
            return {"ok": False, "message": "Hàng đợi hạt giống đang trống! Hãy nhập thêm từ vựng ở Sổ từ vựng."}

        plot["word_data"] = word_data
        plot["growth"] = 1
        plot["is_vip"] = False
        plot["withered"] = False
        plot["cooldown_until"] = 0
        self._add_log(f"Gieo hạt giống mới vào Ô đất #{int(plot_id)+1}.")
        return {"ok": True, "message": f"🌱 Đã gieo linh thảo vào Ô đất #{int(plot_id)+1}!"}

    def _action_water_plant(self, payload: dict) -> dict:
        """
        Khi người chơi bấm Tưới nước:
        - Kiểm tra điều kiện hợp lệ.
        - Kiểm tra tỷ lệ 30% xuất hiện Random Event (Kỳ Ngộ) từ vocab_pool (với giãn cách tối thiểu 2 lần tưới).
        - Nếu không có sự kiện thì mở câu hỏi Tưới nước bình thường.
        """
        state = self.profiles[self.current_profile]
        pool = state.get("vocab_pool", [])

        if len(pool) < 4:
            return {
                "ok": False,
                "message": f"Thư mục 【{state.get('folder_name', 'Hiện tại')}】 chỉ có {len(pool)} từ vựng!\nCần tối thiểu 4 từ vựng để tạo câu hỏi. Vui lòng thêm từ hoặc chọn Folder khác!"
            }

        plot_id = str(payload.get("plot_id"))
        plot = state["plots"].get(plot_id)

        if not plot or not plot.get("word_data"):
            return self._action_plant_seed({"plot_id": plot_id})

        if state["energy"] < 5:
            return {"ok": False, "message": "Linh Khí đã cạn (<5)! Hãy dùng Hồi Linh Đan trong Túi đồ hoặc Bảo các!"}

        now = time.time()
        cd_remain = int(plot.get("cooldown_until", 0) - now)
        if cd_remain > 0:
            return {
                "ok": False,
                "message": f"Linh thảo đang bị tổn thương linh khí (Cooldown {cd_remain}s)! Hãy đợi hoặc dùng 'Tịnh Thủy Phù'."
            }

        if plot["growth"] >= 3:
            return {"ok": False, "message": "🌳 Linh thảo đã Trưởng Thành (3/3)! Hãy bấm nút 'Thu hoạch' để nhận Linh Thạch & Tu Vi!"}

        # Kiểm tra 30% cơ hội xuất hiện Sự kiện ngẫu nhiên (Kỳ Ngộ) nếu đã cách ít nhất 2 lượt tưới
        waters_since = state.get("waters_since_last_event", 0)
        if waters_since >= 2 and random.random() < 0.30:
            ev = self._generate_random_event_from_pool(pool)
            if ev:
                state["waters_since_last_event"] = 0
                state["random_event"] = ev
                return {"ok": True, "random_event": ev}

        state["waters_since_last_event"] = waters_since + 1
        quiz = self._generate_simple_quiz(plot, pool)
        return {"ok": True, "quiz": quiz}

    def _generate_simple_quiz(self, plot: dict, pool: list) -> dict:
        """
        Tạo câu hỏi Tưới nước lấy 100% đáp án đúng và đáp án sai từ vocab_pool của Folder đang chọn.
        """
        w = plot["word_data"]
        word_zh = w.get("word", "").strip()
        pinyin_correct = (w.get("pinyin") or self._to_pinyin(word_zh)).strip()
        hanviet = (w.get("hanviet") or "").strip().upper()
        meaning_vi = (w.get("meaning") or "").split("|")[0].strip()
        level_tag = (w.get("hsk") or "ABC").strip().upper()
        next_stage = plot["growth"] + 1

        other_items = [item for item in pool if item.get("word", "").strip() != word_zh]

        if next_stage == 1:
            distractors = []
            for item in other_items:
                z = item.get("word", "").strip()
                if z and z not in distractors:
                    distractors.append(z)
            options = random.sample(distractors, min(3, len(distractors))) + [word_zh]
            random.shuffle(options)

            return {
                "stage": 1,
                "mode": "choice_2x2",
                "level_badge": level_tag,
                "stage_badge": "CHỌN CHỮ HÁN: 1 / 3",
                "main_display": meaning_vi,
                "hanviet_display": hanviet,
                "sub_display": f"Pinyin gợi ý: {pinyin_correct}",
                "options": options,
                "correct_answer": word_zh,
                "explanation": f"• Từ vựng: {word_zh} [{pinyin_correct}]\n• Hán Việt: {hanviet}\n• Nghĩa: {meaning_vi}"
            }

        elif next_stage == 2:
            distractor_pys = []
            for item in other_items:
                p = (item.get("pinyin") or self._to_pinyin(item.get("word", ""))).strip()
                if p and p != pinyin_correct and p not in distractor_pys:
                    distractor_pys.append(p)

            if len(distractor_pys) >= 3:
                options = random.sample(distractor_pys, 3) + [pinyin_correct]
            else:
                fake_pys = self._make_confusing_pinyins(word_zh, pinyin_correct)
                options = (distractor_pys + fake_pys)[:3] + [pinyin_correct]
            random.shuffle(options)

            return {
                "stage": 2,
                "mode": "choice_2x2",
                "level_badge": level_tag,
                "stage_badge": "PINYIN: 2 / 3",
                "main_display": word_zh,
                "hanviet_display": hanviet,
                "sub_display": meaning_vi,
                "options": options,
                "correct_answer": pinyin_correct,
                "explanation": f"• Từ vựng: {word_zh} đọc là [{pinyin_correct}]\n• Nghĩa: {meaning_vi}"
            }

        else:
            return {
                "stage": 3,
                "mode": "typing",
                "level_badge": level_tag,
                "stage_badge": "GÕ CHỮ HÁN: 3 / 3",
                "main_display": meaning_vi,
                "hanviet_display": hanviet,
                "sub_display": f"Pinyin: {pinyin_correct}",
                "options": [],
                "correct_answer": word_zh,
                "explanation": f"• Đáp án chuẩn: {word_zh} [{pinyin_correct}]\n• Nghĩa: {meaning_vi}"
            }

    @staticmethod
    def _make_confusing_pinyins(word_zh: str, correct_py: str) -> list:
        char_pys = [x[0] for x in pypinyin.pinyin(word_zh, style=pypinyin.Style.TONE)]
        spaced_py = " ".join(char_pys)
        tone_map_1 = {"ā": "á", "á": "ǎ", "ǎ": "à", "à": "ā", "ē": "é", "é": "ě", "ě": "è", "è": "ē", "ī": "í", "í": "ǐ", "ǐ": "ì", "ì": "ī", "ō": "ó", "ó": "ǒ", "ǒ": "ò", "ò": "ō", "ū": "ú", "ú": "ǔ", "ǔ": "ù", "ù": "ū"}
        tone_map_2 = {"ā": "ǎ", "á": "à", "ǎ": "ā", "à": "á", "ē": "ě", "é": "è", "ě": "ē", "è": "é", "ī": "ǐ", "í": "ì", "ǐ": "ī", "ì": "í", "ō": "ǒ", "ó": "ò", "ǒ": "ō", "ò": "ó", "ū": "ǔ", "ú": "ù", "ǔ": "ū", "ù": "ú"}
        results = []
        for cmap in (tone_map_1, tone_map_2):
            mutated = "".join([cmap.get(ch, ch) for ch in spaced_py])
            if mutated != correct_py and mutated not in results:
                results.append(mutated)
        while len(results) < 3:
            results.append(correct_py + " ")
        return results

    def _get_active_pet_bonuses(self) -> tuple[int, int]:
        state = self.profiles[self.current_profile]
        active_id = state.get("pets", {}).get("active_pet", "thanh_lan_loc")
        pet_cfg = self.SPIRIT_PETS.get(active_id, self.SPIRIT_PETS["thanh_lan_loc"])
        lvl = state.get("pets", {}).get("owned", {}).get(active_id, {}).get("level", 1)
        return pet_cfg["tu_vi_bonus"] * lvl, pet_cfg["gold_bonus"] * lvl

    def _action_answer_quiz(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        plot_id = str(payload.get("plot_id"))
        user_answer = str(payload.get("answer", "")).strip()
        correct_answer = str(payload.get("correct_answer", "")).strip()
        explanation = payload.get("explanation", "")
        is_timeout = bool(payload.get("timeout", False))

        plot = state["plots"].get(plot_id)
        if not plot:
            return {"ok": False, "message": "Ô đất không hợp lệ!"}

        w_zh = plot["word_data"].get("word", "") if plot.get("word_data") else ""
        state["stats"]["water_count"] = state["stats"].get("water_count", 0) + 1

        if not is_timeout and user_answer.lower() == correct_answer.lower():
            plot["growth"] = min(3, plot["growth"] + 1)
            plot["withered"] = False
            plot["cooldown_until"] = 0

            pet_tu_vi, _ = self._get_active_pet_bonuses()
            gained_tu_vi = 25 + pet_tu_vi
            state["tu_vi"] += gained_tu_vi
            state["energy"] = min(state["max_energy"], state["energy"] + 10)
            state["stats"]["correct_answers"] = state["stats"].get("correct_answers", 0) + 1

            self._add_log(f"Tưới nước ĐÚNG tại Ô #{int(plot_id)+1} (+{gained_tu_vi} Tu Vi, +10 Linh Khí).")
            return {
                "ok": True,
                "correct": True,
                "message": (
                    f"✅ TRẢ LỜI CHÍNH XÁC!\n\n"
                    f"• Linh thảo phát triển lên: {plot['growth']} / 3\n"
                    f"• Phần thưởng: +{gained_tu_vi} Tu Vi & +10 Linh Khí\n\n"
                    f"{explanation}"
                )
            }
        else:
            state["energy"] = max(0, state["energy"] - 5)
            plot["withered"] = True
            plot["cooldown_until"] = time.time() + 30
            if w_zh:
                wrong_map = state.setdefault("wrong_words", {})
                wrong_map[w_zh] = wrong_map.get(w_zh, 0) + 1

            self._add_log(f"Tưới nước SAI tại Ô #{int(plot_id)+1} (-5 Linh Khí, Cooldown 30s).")
            return {
                "ok": True,
                "correct": False,
                "message": (
                    f"❌ TRẢ LỜI CHƯA ĐÚNG!\n\n"
                    f"• Đáp án của bạn: {user_answer}\n"
                    f"• Đáp án chính xác: {correct_answer}\n"
                    f"• Hình phạt: -5 Linh Khí & Cooldown 30 giây\n\n"
                    f"{explanation}"
                )
            }

    def _action_harvest(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        plot_id = str(payload.get("plot_id"))
        plot = state["plots"].get(plot_id)

        if not plot or not plot.get("word_data"):
            return {"ok": False, "message": "Ô đất đang trống!"}
        if plot["growth"] < 3:
            return {"ok": False, "message": f"Linh thảo chưa trưởng thành ({plot['growth']}/3)! Hãy tưới nước đạt 3/3 trước."}

        harvested_word = plot["word_data"].get("word", "")
        harvested_meaning = plot["word_data"].get("meaning", "")
        _, pet_gold = self._get_active_pet_bonuses()

        base_gold = 150 if plot.get("is_vip") else 50
        total_gold = base_gold + pet_gold
        gained_tu_vi = 80 if plot.get("is_vip") else 40

        state["gold"] += total_gold
        state["tu_vi"] += gained_tu_vi
        state["stats"]["total_harvested"] = state["stats"].get("total_harvested", 0) + 1

        state["seed_queue"].append(plot["word_data"])
        next_seed = state["seed_queue"].pop(0) if state["seed_queue"] else None

        plot["word_data"] = next_seed
        plot["growth"] = 1 if next_seed else 0
        plot["is_vip"] = False
        plot["withered"] = False
        plot["cooldown_until"] = 0

        self._add_log(f"Thu hoạch linh thảo '{harvested_word}' (+{total_gold} Linh Thạch, +{gained_tu_vi} Tu Vi).")
        return {
            "ok": True,
            "reward": total_gold,
            "tu_vi_gained": gained_tu_vi,
            "message": (
                f"🌾 Thu hoạch đại thành công linh thảo 【{harvested_word}】 ({harvested_meaning})!\n"
                f"• Nhận: +{total_gold} Linh Thạch\n"
                f"• Nhận: +{gained_tu_vi} Tu Vi\n"
                f"🌱 Đã tự động gieo mầm linh thảo mới vào ô đất!"
            )
        }

    def _action_use_item(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        item_id = payload.get("item_id")
        plot_id = str(payload.get("plot_id", "0"))

        if state["inventory"].get(item_id, 0) <= 0:
            return {"ok": False, "message": "Trong Túi Đồ đã hết vật phẩm này! Hãy ghé Tàng Bảo Các để mua thêm."}

        if item_id == "tra_sua":
            state["energy"] = state["max_energy"]
            state["inventory"][item_id] -= 1
            self._add_log("Sử dụng Hồi Linh Đan: Hồi đầy 200/200 Linh Khí.")
            return {"ok": True, "message": "💊 Đã dùng Hồi Linh Đan: Linh Khí hồi phục 200 / 200!"}

        if item_id == "tay_tuy_dan":
            state["tu_vi"] += 120
            state["inventory"][item_id] -= 1
            self._add_log("Sử dụng Tẩy Tủy Đan: Tăng +120 Tu Vi.")
            return {"ok": True, "message": "🔮 Đã dùng Tẩy Tủy Đan: Kinh mạch thông suốt, tăng +120 Tu Vi!"}

        plot = state["plots"].get(plot_id)
        if not plot or not plot.get("word_data"):
            return {"ok": False, "message": "Hãy chọn một ô đất đang có linh thảo trước khi dùng pháp bảo này!"}

        if item_id == "thuoc_tru_sau":
            if plot["growth"] >= 3:
                return {"ok": False, "message": "Linh thảo đã Trưởng Thành (3/3) rồi, hãy bấm Thu hoạch!"}
            plot["growth"] = min(3, plot["growth"] + 1)
            state["inventory"][item_id] -= 1
            self._add_log(f"Dùng Bùa May Mắn lên Ô #{int(plot_id)+1} (+1 Growth).")
            return {"ok": True, "message": "📜 Đã dùng Bùa May Mắn: Linh thảo tăng +1 Growth!"}

        elif item_id == "phan_bon":
            if plot["growth"] >= 3:
                return {"ok": False, "message": "Linh thảo đã Trưởng Thành (3/3) rồi, hãy bấm Thu hoạch!"}
            plot["growth"] = min(3, plot["growth"] + 2)
            state["inventory"][item_id] -= 1
            self._add_log(f"Dùng Tiên Lộ Linh Dịch lên Ô #{int(plot_id)+1} (+2 Growth).")
            return {"ok": True, "message": "🧪 Đã tưới Tiên Lộ Linh Dịch: Linh thảo tăng vọt +2 Growth!"}

        elif item_id == "hat_vip":
            if plot.get("is_vip"):
                return {"ok": False, "message": "Linh thảo này đã là Tiên Phẩm rồi!"}
            plot["is_vip"] = True
            state["inventory"][item_id] -= 1
            self._add_log(f"Nâng cấp Ô #{int(plot_id)+1} thành Hạt Giống Tiên Phẩm.")
            return {"ok": True, "message": "🌟 Đã nâng cấp lên Hạt Giống Tiên Phẩm (Thu hoạch 150 Linh Thạch)!"}

        elif item_id == "binh_nuoc":
            plot["withered"] = False
            plot["cooldown_until"] = 0
            state["inventory"][item_id] -= 1
            self._add_log(f"Dùng Tịnh Thủy Phù thanh tẩy Ô #{int(plot_id)+1}.")
            return {"ok": True, "message": "💧 Đã dùng Tịnh Thủy Phù: Xóa bỏ hoàn toàn Cooldown!"}

        return {"ok": False, "message": "Vật phẩm không hợp lệ!"}

    def _action_breakthrough(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        cur_idx = state.get("realm_idx", 0)
        if cur_idx >= len(self.REALMS) - 1:
            return {"ok": False, "message": "Bạn đã đạt tới đỉnh phong cảnh giới hiện tại!"}

        req_tu_vi = self.REALMS[cur_idx][1]
        if state["tu_vi"] < req_tu_vi:
            missing = req_tu_vi - state["tu_vi"]
            return {"ok": False, "message": f"Chưa đủ Tu Vi để đột phá! Còn thiếu {missing} Tu Vi nữa."}

        state["tu_vi"] -= req_tu_vi
        state["realm_idx"] = cur_idx + 1
        state["breakthrough_count"] = state.get("breakthrough_count", 0) + 1
        new_realm = self.REALMS[state["realm_idx"]][0]
        state["max_tu_vi"] = self.REALMS[state["realm_idx"]][1]
        self._add_log(f"⚡ Đột phá thành công lên cảnh giới 【{new_realm}】!")
        return {
            "ok": True,
            "new_realm": new_realm,
            "message": f"⚡ Linh khí quán đỉnh! Chúc mừng đạo hữu đột phá thành công lên cảnh giới 【{new_realm}】!"
        }

    def _action_resolve_event(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        ev = state.get("random_event")
        if not ev:
            return {"ok": False, "message": "Sự kiện đã kết thúc."}

        ans = str(payload.get("answer", "")).strip()
        correct = str(ev.get("correct", "")).strip()
        expl = ev.get("explanation", "")
        code = ev.get("code", "KY_NGO")
        w_zh = ev.get("word", "")
        state["random_event"] = None

        if ans == correct:
            gold_rw = ev.get("reward_gold", 0)
            tu_vi_rw = ev.get("reward_tu_vi", 0)
            eng_rw = ev.get("reward_energy", 0)
            bonus_item = ev.get("bonus_item")

            state["gold"] += gold_rw
            state["tu_vi"] += tu_vi_rw
            state["energy"] = min(state["max_energy"], state["energy"] + eng_rw)
            state["stats"]["correct_answers"] = state["stats"].get("correct_answers", 0) + 1

            rw_parts = []
            if gold_rw:
                rw_parts.append(f"+{gold_rw} Linh Thạch")
            if tu_vi_rw:
                rw_parts.append(f"+{tu_vi_rw} Tu Vi")
            if eng_rw:
                rw_parts.append(f"+{eng_rw} Linh Khí")
            if bonus_item and bonus_item in self.SHOP_ITEMS:
                state["inventory"][bonus_item] = state["inventory"].get(bonus_item, 0) + 1
                rw_parts.append(f"+1 {self.SHOP_ITEMS[bonus_item]['name']}")

            rw_summary = ", ".join(rw_parts) if rw_parts else "Vượt qua thử thách"
            self._add_log(f"Vượt qua sự kiện '{ev['title']}' ({rw_summary}).")

            return {
                "ok": True,
                "correct": True,
                "open_merchant_discount": (code == "THUONG_NHAN"),
                "message": (
                    f"✅ TRẢ LỜI CHÍNH XÁC!\n\n"
                    f"🎉 Kết quả: {ev['title']} thành công!\n"
                    f"🎁 Phần thưởng: {rw_summary}\n\n"
                    f"📖 Giải thích từ vựng:\n{expl}"
                )
            }
        else:
            pen_eng = ev.get("penalty_energy", 0)
            state["energy"] = max(0, state["energy"] - pen_eng)
            if w_zh:
                wrong_map = state.setdefault("wrong_words", {})
                wrong_map[w_zh] = wrong_map.get(w_zh, 0) + 1

            pen_str = f"Bị trừ -{pen_eng} Linh Khí." if pen_eng > 0 else "Không nhận được phần thưởng."
            self._add_log(f"Thất bại sự kiện '{ev['title']}' ({pen_str}).")
            return {
                "ok": True,
                "correct": False,
                "open_merchant_discount": False,
                "message": (
                    f"❌ TRẢ LỜI CHƯA ĐÚNG!\n\n"
                    f"• Đáp án bạn chọn: {ans}\n"
                    f"• Đáp án chính xác: {correct}\n"
                    f"• Hậu quả: {pen_str}\n\n"
                    f"📖 Giải thích từ vựng:\n{expl}"
                )
            }

    def _action_activate_pet(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        pet_id = payload.get("pet_id")
        if pet_id not in self.SPIRIT_PETS:
            return {"ok": False, "message": "Linh thú không tồn tại!"}

        owned = state["pets"].setdefault("owned", {})
        pet_cfg = self.SPIRIT_PETS[pet_id]

        if pet_id not in owned:
            cost = pet_cfg["unlock_cost"]
            if state["gold"] < cost:
                return {"ok": False, "message": f"Cần {cost} Linh Thạch để kết khế ước với {pet_cfg['name']}!"}
            state["gold"] -= cost
            owned[pet_id] = {"level": 1, "exp": 0}
            self._add_log(f"Kết khế ước thành công với Linh Thú 【{pet_cfg['name']}】.")

        state["pets"]["active_pet"] = pet_id
        return {"ok": True, "message": f"🐾 Đã chọn 【{pet_cfg['name']}】 đồng hành cùng bạn!"}

    def _action_upgrade_pet(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        pet_id = payload.get("pet_id")
        owned = state["pets"].get("owned", {})
        if pet_id not in owned:
            return {"ok": False, "message": "Bạn chưa sở hữu linh thú này!"}

        cur_lvl = owned[pet_id]["level"]
        cost = cur_lvl * 80
        if state["gold"] < cost:
            return {"ok": False, "message": f"Cần {cost} Linh Thạch để bồi dưỡng linh thú lên Cấp {cur_lvl + 1}!"}

        state["gold"] -= cost
        owned[pet_id]["level"] += 1
        pet_name = self.SPIRIT_PETS[pet_id]["name"]
        self._add_log(f"Bồi dưỡng {pet_name} lên Cấp {owned[pet_id]['level']} (-{cost} Linh Thạch).")
        return {"ok": True, "message": f"✨ Đã bồi dưỡng 【{pet_name}】 lên Cấp {owned[pet_id]['level']}!"}

    def get_quests_status(self) -> list:
        state = self.profiles[self.current_profile]
        stats = state.get("stats", {})
        claimed = set(state.get("quests_claimed", []))

        quests = [
            {
                "id": "q_daily_water",
                "group": "Nhiệm vụ ngày",
                "title": "Chăm sóc Linh Điền",
                "desc": "Tưới nước linh thảo 3 lần",
                "progress": min(3, stats.get("water_count", 0)),
                "target": 3,
                "reward_gold": 60,
                "reward_tu_vi": 40
            },
            {
                "id": "q_daily_harvest",
                "group": "Nhiệm vụ ngày",
                "title": "Thu hoạch Linh Thảo",
                "desc": "Thu hoạch thành công 2 cây trưởng thành",
                "progress": min(2, stats.get("total_harvested", 0)),
                "target": 2,
                "reward_gold": 80,
                "reward_tu_vi": 50
            },
            {
                "id": "q_weekly_correct",
                "group": "Nhiệm vụ tuần",
                "title": "Tinh thông Hán Ngữ",
                "desc": "Trả lời đúng 15 câu hỏi từ vựng",
                "progress": min(15, stats.get("correct_answers", 0)),
                "target": 15,
                "reward_gold": 200,
                "reward_tu_vi": 150
            },
            {
                "id": "q_special_realm",
                "group": "Nhiệm vụ đặc biệt",
                "title": "Thám hiểm Bí Cảnh",
                "desc": "Chinh phục thành công 1 Bí Cảnh",
                "progress": min(1, stats.get("realms_cleared", 0)),
                "target": 1,
                "reward_gold": 150,
                "reward_tu_vi": 120
            }
        ]
        for q in quests:
            q["claimed"] = q["id"] in claimed
            q["completed"] = q["progress"] >= q["target"]
        return quests

    def _action_claim_quest(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        qid = payload.get("quest_id")
        quests = self.get_quests_status()
        target_q = next((q for q in quests if q["id"] == qid), None)
        if not target_q:
            return {"ok": False, "message": "Nhiệm vụ không hợp lệ!"}
        if target_q["claimed"]:
            return {"ok": False, "message": "Bạn đã nhận thưởng nhiệm vụ này rồi!"}
        if not target_q["completed"]:
            return {"ok": False, "message": "Nhiệm vụ chưa hoàn thành!"}

        state["quests_claimed"].append(qid)
        state["gold"] += target_q["reward_gold"]
        state["tu_vi"] += target_q["reward_tu_vi"]
        self._add_log(f"Nhận thưởng nhiệm vụ '{target_q['title']}' (+{target_q['reward_gold']} Linh Thạch, +{target_q['reward_tu_vi']} Tu Vi).")
        return {
            "ok": True,
            "message": f"🎁 Nhận thưởng thành công: +{target_q['reward_gold']} Linh Thạch & +{target_q['reward_tu_vi']} Tu Vi!"
        }

    def _action_complete_secret_realm(self, payload: dict) -> dict:
        state = self.profiles[self.current_profile]
        realm_id = payload.get("realm_id")
        victory = bool(payload.get("victory", False))
        correct_cnt = int(payload.get("correct_count", 0))
        wrong_cnt = int(payload.get("wrong_count", 0))
        bonus_gold_collected = int(payload.get("bonus_gold", 0))

        realm_cfg = next((r for r in self.SECRET_REALMS if r["id"] == realm_id), self.SECRET_REALMS[0])
        state["stats"]["correct_answers"] = state["stats"].get("correct_answers", 0) + correct_cnt

        if victory:
            rw_gold = realm_cfg["reward_gold"] + bonus_gold_collected
            rw_tu_vi = realm_cfg["reward_tu_vi"]
            rw_item = realm_cfg.get("reward_item")

            state["gold"] += rw_gold
            state["tu_vi"] += rw_tu_vi
            state["stats"]["realms_cleared"] = state["stats"].get("realms_cleared", 0) + 1

            item_msg = ""
            if rw_item and rw_item in self.SHOP_ITEMS:
                state["inventory"][rw_item] = state["inventory"].get(rw_item, 0) + 1
                item_msg = f"\n• Vật phẩm: +1 {self.SHOP_ITEMS[rw_item]['name']}"

            self._add_log(f"Chinh phục {realm_cfg['name']} thành công (+{rw_gold} Linh Thạch, +{rw_tu_vi} Tu Vi).")
            return {
                "ok": True,
                "victory": True,
                "message": (
                    f"🏆 CHIẾN THẮNG 【{realm_cfg['name'].upper()}】!\n"
                    f"Đã đánh bại Boss: {realm_cfg['boss_name']}!\n\n"
                    f"• Số câu trả lời đúng: {correct_cnt} câu (Sai: {wrong_cnt})\n"
                    f"• Linh Thạch nhận được: +{rw_gold} Linh Thạch\n"
                    f"• Tu Vi nhận được: +{rw_tu_vi} Tu Vi{item_msg}"
                )
            }
        else:
            # Nếu thất bại vẫn giữ được một nửa số Linh Thạch nhặt được dọc đường, không trừ Linh Thạch sẵn có
            kept_gold = bonus_gold_collected // 2
            if kept_gold > 0:
                state["gold"] += kept_gold
            self._add_log(f"Thám hiểm {realm_cfg['name']} thất bại (Đúng {correct_cnt} câu).")
            return {
                "ok": True,
                "victory": False,
                "message": (
                    f"💨 THÁM HIỂM THẤT BẠI!\n"
                    f"HP trong Bí Cảnh đã cạn khi giao chiến tại {realm_cfg['name']}.\n\n"
                    f"• Số câu đúng: {correct_cnt} | Số câu sai: {wrong_cnt}\n"
                    f"• Linh Thạch nhặt được giữ lại: +{kept_gold} Linh Thạch"
                )
            }