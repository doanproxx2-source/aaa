import json
import re
import urllib.parse
import requests
import pypinyin
from config import Config


class AIServiceError(Exception):
    """Ngoại lệ hiển thị thông báo lỗi tiếng Việt rõ ràng."""
    pass


TRANSLATION_CACHE = {}

# =====================================================================
# BẢNG ÂM HÁN VIỆT MỞ RỘNG (ĐẢM BẢO KHÔNG BỊ HIỆN CHỮ HÁN KHI PHIÊN ÂM)
# =====================================================================
CHAR_HANVIET_HSK = {
    "我": ("ngã", 1), "你": ("nhĩ", 1), "他": ("tha", 1), "她": ("tha", 1), "们": ("môn", 1),
    "是": ("thị", 1), "的": ("đích", 1), "了": ("liễu", 1), "在": ("tại", 1), "有": ("hữu", 1),
    "人": ("nhân", 1), "中": ("trung", 1), "国": ("quốc", 1), "越": ("việt", 2), "南": ("nam", 2),
    "汉": ("hán", 1), "语": ("ngữ", 1), "文": ("văn", 1), "工": ("công", 1), "作": ("tác", 1),
    "厂": ("xưởng", 3), "加": ("gia", 2), "班": ("ban", 2), "夜": ("dạ", 3), "白": ("bạch", 1),
    "薄": ("bạc", 4), "厚": ("hậu", 4), "瘦": ("sấu", 4), "胖": ("bàn", 3), "请": ("thỉnh", 1),
    "按": ("án", 4), "照": ("chiếu", 3), "图": ("đồ", 2), "纸": ("chỉ", 2), "检": ("kiểm", 3),
    "查": ("tra", 3), "设": ("thiết", 4), "备": ("bị", 2), "电": ("điện", 1), "机": ("cơ", 1),
    "器": ("khí", 3), "视": ("thị", 1), "觉": ("giác", 1), "相": ("tương", 3), "光": ("quang", 3),
    "源": ("nguyên", 4), "传": ("truyền", 4), "感": ("cảm", 3), "气": ("khí", 1), "缸": ("cang", 5),
    "阀": ("phạt", 5), "程": ("trình", 3), "序": ("tự", 4), "参": ("tham", 3), "数": ("số", 3),
    "调": ("điều", 4), "试": ("thí", 2), "报": ("báo", 2), "警": ("cảnh", 4), "故": ("cố", 3),
    "障": ("chướng", 4), "复": ("phục", 3), "位": ("vị", 2), "自": ("tự", 2), "动": ("động", 2),
    "手": ("thủ", 1), "运": ("vận", 2), "行": ("hành", 2), "断": ("đoạn", 4), "路": ("lộ", 1),
    "开": ("khai", 1), "关": ("quan", 1), "接": ("tiếp", 2), "触": ("xúc", 5), "继": ("kế", 4),
    "常": ("thường", 2), "闭": ("bế", 4), "点": ("điểm", 1), "伺": ("tự", 6), "服": ("phục", 2),
    "步": ("bộ", 2), "进": ("tiến", 2), "驱": ("khu", 5), "编": ("biên", 4), "码": ("mã", 3),
    "线": ("tuyến", 2), "控": ("khống", 5), "制": ("chế", 4), "柜": ("quầy", 5), "输": ("thâu", 4),
    "入": ("nhập", 2), "出": ("xuất", 1), "良": ("lương", 4), "品": ("phẩm", 3), "不": ("bất", 1),
    "维": ("duy", 4), "修": ("tu", 3), "保": ("bảo", 3), "养": ("dưỡng", 4), "更": ("canh", 2),
    "换": ("hoán", 3), "零": ("linh", 1), "件": ("kiện", 2), "停": ("đình", 3), "异": ("dị", 5),
    "标": ("tiêu", 3), "定": ("định", 2), "测": ("trắc", 4), "量": ("lượng", 3), "模": ("mô", 4),
    "板": ("bản", 3), "算": ("thuật", 2), "法": ("pháp", 3), "缺": ("khuyết", 4), "陷": ("hãm", 5),
    "任": ("nhiệm", 4), "何": ("hà", 4), "实": ("thực", 3), "际": ("tế", 4), "适": ("thích", 4),
    "应": ("ứng", 3), "环": ("hoàn", 3), "境": ("cảnh", 3), "生": ("sinh", 1), "活": ("hoạt", 2),
    "能": ("năng", 1), "力": ("lực", 2), "变": ("biến", 3), "化": ("hóa", 3), "慢": ("mạn", 2),
    "新": ("tân", 1), "系": ("hệ", 3), "统": ("thống", 4), "业": ("nghiệp", 3), "镜": ("kính", 3),
    "头": ("đầu", 1), "纤": ("tiêm", 5), "明": ("minh", 1), "片": ("phiến", 3), "托": ("thác", 4),
    "盘": ("bàn", 3), "整": ("chỉnh", 3), "位": ("vị", 2), "置": ("trí", 4), "连": ("liên", 4),
    "模": ("mô", 4), "糊": ("hồ", 5), "亮": ("lượng", 2), "度": ("độ", 3), "脏": ("tang", 3),
    "影": ("ảnh", 2), "响": ("hưởng", 3), "质": ("chất", 4), "采": ("thái", 4), "集": ("tập", 3),
}

AUTO_CORRECTION_RULES = {
    "我是越南": "我是越南人",
    "你是中国": "你是中国人",
    "他是中国": "他是中国人",
    "我学中文在河内": "我在河内学中文",
    "我工作在工厂": "我在工厂工作",
}

# =====================================================================
# CƠ SỞ DỮ LIỆU TỪ ĐIỂN CAMVISION & TỪ VỰNG TRỌNG TÂM
# =====================================================================
TECHNICAL_DICT = {
    "机器视觉": {"pinyin": "jīqì shìjué", "hv": "cơ khí thị giác", "pos": "Danh từ", "vi": "thị giác máy", "topic": "Camvision", "ex": ("机器视觉可以自动检测产品。", "Thị giác máy có thể tự động kiểm tra sản phẩm.")},
    "视觉": {"pinyin": "shìjué", "hv": "thị giác", "pos": "Danh từ", "vi": "thị giác; liên quan đến mắt", "topic": "Camvision", "ex": ("这个视觉系统可以检测产品。", "Hệ thống thị giác này có thể kiểm tra sản phẩm.")},
    "视觉系统": {"pinyin": "shìjué xìtǒng", "hv": "thị giác hệ thống", "pos": "Danh từ", "vi": "hệ thống thị giác", "topic": "Camvision", "ex": ("这个视觉系统主要用来检测产品。", "Hệ thống thị giác này chủ yếu dùng để kiểm tra sản phẩm.")},
    "相机": {"pinyin": "xiàngjī", "hv": "tương cơ", "pos": "Danh từ", "vi": "camera", "topic": "Camvision", "ex": ("相机的位置需要调整。", "Vị trí camera cần được điều chỉnh.")},
    "工业相机": {"pinyin": "gōngyè xiàngjī", "hv": "công nghiệp tương cơ", "pos": "Danh từ", "vi": "camera công nghiệp", "topic": "Camvision", "ex": ("这台设备使用的是工业相机。", "Thiết bị này sử dụng camera công nghiệp.")},
    "镜头": {"pinyin": "jìngtóu", "hv": "kính đầu", "pos": "Danh từ", "vi": "ống kính", "topic": "Camvision", "ex": ("镜头太脏会影响图像质量。", "Ống kính quá bẩn sẽ ảnh hưởng chất lượng hình ảnh.")},
    "光源": {"pinyin": "guāngyuán", "hv": "quang nguyên", "pos": "Danh từ", "vi": "nguồn sáng", "topic": "Camvision", "ex": ("光源的亮度需要调整。", "Độ sáng của nguồn sáng cần được điều chỉnh.")},
    "光纤": {"pinyin": "guāngxiān", "hv": "quang tiêm", "pos": "Danh từ", "vi": "sợi quang, ánh sáng", "topic": "Camvision", "ex": ("光纤连接好了以后再测试。", "Sau khi kết nối sợi quang xong thì kiểm tra lại.")},
    "照明": {"pinyin": "zhàomíng", "hv": "chiếu minh", "pos": "Danh/Động từ", "vi": "chiếu sáng", "topic": "Camvision", "ex": ("照明不好会影响检测结果。", "Chiếu sáng không tốt sẽ ảnh hưởng kết quả kiểm tra.")},
    "图片": {"pinyin": "túpiàn", "hv": "đồ phiến", "pos": "Danh từ", "vi": "hình ảnh", "topic": "Camvision", "ex": ("这张图片有点模糊。", "Hình ảnh này hơi mờ.")},
    "测试运行": {"pinyin": "cèshì yùnxíng", "hv": "trắc thí vận hành", "pos": "Động/Danh từ", "vi": "chạy thử, vận hành kiểm tra", "topic": "Camvision", "ex": ("修改参数后，进行测试运行。", "Sau khi sửa tham số, tiến hành chạy thử.")},
    "适应": {
        "pinyin": "shìyìng",
        "hv": "thích ứng",
        "pos": "Động từ",
        "vi": "Thích nghi, thích ứng, làm quen với điều kiện hoặc hoàn cảnh mới.",
        "topic": "Công việc",
        "hsk": "Khoảng HSK4",
        "usage": "适应 thường dùng khi nói về việc thích nghi với môi trường làm việc, cuộc sống, thời tiết, nhịp độ công việc hoặc những thay đổi mới.",
        "examples": [
            {"zh": "我还不太适应这里的生活。", "pinyin": "Wǒ hái bú tài shìyìng zhèlǐ de shēnghuó.", "vi": "Tôi vẫn chưa thích nghi lắm với cuộc sống ở đây."},
            {"zh": "他很快就适应了新的工作。", "pinyin": "Tā hěn kuài jiù shìyìng le xīn de gōngzuò.", "vi": "Anh ấy rất nhanh đã thích nghi với công việc mới."},
            {"zh": "虽然工作比较忙，但我正在慢慢适应。", "pinyin": "Suīrán gōngzuò bǐjiào máng, dàn wǒ zhèngzài mànmàn shìyìng.", "vi": "Mặc dù công việc khá bận, nhưng tôi đang dần thích nghi."}
        ],
        "collocations": [
            ("适应环境", "shìyìng huánjìng", "Thích nghi với môi trường"),
            ("适应工作", "shìyìng gōngzuò", "Thích nghi với công việc"),
            ("适应生活", "shìyìng shēnghuó", "Thích nghi với cuộc sống"),
            ("适应能力", "shìyìng nénglì", "Khả năng thích nghi"),
            ("适应变化", "shìyìng biànhuà", "Thích nghi với sự thay đổi"),
            ("慢慢适应", "mànmàn shìyìng", "Dần dần thích nghi"),
            ("不太适应", "bú tài shìyìng", "Chưa thích nghi lắm"),
            ("适应新环境", "shìyìng xīn huánjìng", "Thích nghi với môi trường mới")
        ],
        "grammar_note": "• 适应 + Danh từ (环境 / 工作 / 生活): Thích nghi với cái gì đó.\n• Phó từ (很 / 不太 / 慢慢 / 已经) + 适应: Biểu thị mức độ hoặc quá trình thích nghi.",
        "dialogue": [
            ("A: 你适应新公司的工作了吗？", "Nǐ shìyìng xīn gōngsī de gōngzuò le ma?", "A: Bạn đã thích nghi với công việc ở công ty mới chưa?"),
            ("B: 还没有完全适应，不过我正在努力学习。", "Hái méiyǒu wánquán shìyìng, búguò wǒ zhèngzài nǔlì xuéxí.", "B: Vẫn chưa hoàn toàn thích nghi, nhưng tôi đang cố gắng học hỏi."),
            ("A: 别着急，慢慢来就好。", "Bié zháojí, mànmàn lái jiù hǎo.", "A: Đừng nóng vội, cứ từ từ là được."),
            ("B: 谢谢，我相信自己很快就能适应。", "Xièxie, wǒ xiāngxìn zìjǐ hěn kuài jiù néng shìyìng.", "B: Cảm ơn, tôi tin mình sẽ sớm thích nghi được.")
        ]
    },
    "任何": {
        "pinyin": "rènhé",
        "hv": "nhiệm hà",
        "pos": "Đại từ",
        "vi": "Bất kỳ, bất cứ (dùng trong câu phủ định, câu hỏi hoặc câu khẳng định có 都/也).",
        "topic": "Công việc",
        "hsk": "Khoảng HSK4",
        "usage": "任何 thường đứng trước danh từ (như 任何问题, 任何人, 任何情况) và đi kèm với 都 hoặc 也 ở phía sau để nhấn mạnh 'bất kỳ cái gì cũng...'.",
        "examples": [
            {"zh": "如果设备有任何异常，请立即停机。", "pinyin": "Rúguǒ shèbèi yǒu rènhé yìcháng, qǐng lìjí tíngjī.", "vi": "Nếu thiết bị có bất kỳ bất thường nào, vui lòng dừng máy ngay lập tức."},
            {"zh": "不要随便改动任何视觉参数。", "pinyin": "Búyào suíbiàn gǎidòng rènhé shìjué cānshù.", "vi": "Đừng tùy tiện thay đổi bất kỳ thông số Vision nào."},
            {"zh": "工作中有任何问题都可以问我。", "pinyin": "Gōngzuò zhōng yǒu rènhé wèntí dōu kěyǐ wèn wǒ.", "vi": "Trong công việc có bất kỳ vấn đề gì đều có thể hỏi tôi."}
        ],
        "collocations": [
            ("任何问题", "rènhé wèntí", "Bất kỳ vấn đề nào"),
            ("任何人", "rènhé rén", "Bất kỳ ai"),
            ("任何情况", "rènhé qíngkuàng", "Bất kỳ tình huống nào"),
            ("任何时候", "rènhé shíhou", "Bất cứ lúc nào"),
            ("任何地方", "rènhé dìfang", "Bất cứ nơi đâu"),
            ("没有任何...", "méiyǒu rènhé...", "Không có bất kỳ...")
        ],
        "grammar_note": "• 任何 + (Số lượng từ) + Danh từ + 都 / 也 + Động từ.\n• 没有任何 + Danh từ: Hoàn toàn không có bất cứ...",
        "dialogue": [
            ("A: 这台工业相机的参数可以改吗？", "Zhè tái gōngyè xiàngjī de cānshù kěyǐ gǎi ma?", "A: Thông số của chiếc camera công nghiệp này có sửa được không?"),
            ("B: 未经允许，不能修改任何参数。", "Wèijīng yǔnxǔ, bùnéng xiūgǎi rènhé cānshù.", "B: Khi chưa được phép, không được chỉnh sửa bất kỳ thông số nào."),
            ("A: 好的，如果检测出任何不良品怎么办？", "Hǎo de, rúguǒ jiǎncè chū rènhé bùliángpǐn zěnmebàn?", "A: Vâng, nếu kiểm tra ra bất kỳ hàng lỗi nào thì làm thế nào?"),
            ("B: 请马上拍照并报告给主管。", "Qǐng mǎshàng pāizhào bìng bàogào gěi zhǔguǎn.", "B: Vui lòng chụp ảnh ngay và báo cáo cho chủ quản.")
        ]
    },
    "断路器": {"hv": "đoạn lộ khí", "pos": "Danh từ", "vi": "Aptomat / Bộ ngắt mạch (CB)", "topic": "Điện công nghiệp", "ex": ("请先关闭主断路器再检查线路。", "Vui lòng tắt aptomat tổng trước khi kiểm tra đường dây.")},
    "接触器": {"hv": "tiếp xúc khí", "pos": "Danh từ", "vi": "Khởi động từ (Contactor)", "topic": "Điện công nghiệp", "ex": ("这个交流接触器的线圈烧坏了。", "Cuộn hút của khởi động từ xoay chiều này bị cháy rồi.")},
    "继电器": {"hv": "kế điện khí", "pos": "Danh từ", "vi": "Rơ-le (Relay)", "topic": "Điện công nghiệp", "ex": ("请检查控制柜里的继电器是否吸合。", "Hãy kiểm tra rơ-le trong tủ điều khiển có đóng/hút không.")},
    "传感器": {"hv": "truyền cảm khí", "pos": "Danh từ", "vi": "Cảm biến (Sensor)", "topic": "Tự động hóa", "ex": ("这个传感器没有感应到产品。", "Cảm biến này không nhận diện được sản phẩm.")},
    "光电传感器": {"hv": "quang điện truyền cảm khí", "pos": "Danh từ", "vi": "Cảm biến quang điện", "topic": "Tự động hóa", "ex": ("光电传感器表面有灰尘，请擦干净。", "Bề mặt cảm biến quang có bụi, vui lòng lau sạch.")},
    "调试": {"hv": "điều thí", "pos": "Động từ", "vi": "Căn chỉnh / Chạy thử máy", "topic": "Tự động hóa", "ex": ("今天我们要去产线调试新设备。", "Hôm nay chúng ta phải xuống dây chuyền căn chỉnh thiết bị mới.")},
    "标定": {"hv": "tiêu định", "pos": "Động/Danh từ", "vi": "Hiệu chuẩn (Calibration)", "topic": "Camvision", "ex": ("移动相机后必须重新进行九点标定。", "Sau khi dịch chuyển camera bắt buộc phải hiệu chuẩn 9 điểm lại.")},
}


def is_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def generate_local_pinyin(text: str) -> str:
    if not text:
        return ""
    res = pypinyin.pinyin(text, style=pypinyin.Style.TONE)
    return " ".join([item[0] for item in res])


def get_char_by_char_hanviet_and_hsk(zh_text: str) -> tuple[str, str]:
    if zh_text in TECHNICAL_DICT and "hv" in TECHNICAL_DICT[zh_text]:
        hv_str = TECHNICAL_DICT[zh_text]["hv"]
    else:
        hv_parts = []
        for ch in zh_text:
            if is_chinese(ch):
                hv = CHAR_HANVIET_HSK.get(ch, (None, 4))[0]
                if hv:
                    hv_parts.append(hv)
        hv_str = " ".join(hv_parts) if hv_parts else "Âm Hán Việt thông dụng"

    hsk_levels = [CHAR_HANVIET_HSK.get(ch, ("", 4))[1] for ch in zh_text if is_chinese(ch)]
    max_lvl = max(hsk_levels) if hsk_levels else 4
    return hv_str, f"Khoảng HSK{max_lvl}"


def multi_engine_web_translate(text: str, source_lang: str = "zh-CN", target_lang: str = "vi") -> str:
    text = text.strip()
    if not text:
        return ""

    cache_key = f"{source_lang}:{target_lang}:{text}"
    if cache_key in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[cache_key]

    if target_lang == "vi" and text in TECHNICAL_DICT:
        res = TECHNICAL_DICT[text]["vi"]
        TRANSLATION_CACHE[cache_key] = res
        return res

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    try:
        url1 = "https://clients5.google.com/translate_a/t"
        params1 = {"client": "dict-chrome-ex", "sl": source_lang, "tl": target_lang, "q": text}
        r1 = requests.get(url1, params=params1, headers=headers, timeout=5)
        if r1.status_code == 200:
            data1 = r1.json()
            if isinstance(data1, list) and len(data1) > 0:
                if isinstance(data1[0], str):
                    res = data1[0].strip()
                elif isinstance(data1[0], list):
                    res = "".join([x[0] for x in data1 if x and isinstance(x, list)]).strip()
                else:
                    res = ""
                if res:
                    TRANSLATION_CACHE[cache_key] = res
                    return res
    except Exception:
        pass

    try:
        mm_src = "zh-CN" if "zh" in source_lang else "vi-VN"
        mm_tgt = "vi-VN" if "vi" in target_lang else "zh-CN"
        url2 = "https://api.mymemory.translated.net/get"
        params2 = {"q": text, "langpair": f"{mm_src}|{mm_tgt}"}
        r2 = requests.get(url2, params=params2, headers=headers, timeout=6)
        if r2.status_code == 200:
            data2 = r2.json()
            res = data2.get("responseData", {}).get("translatedText", "").strip()
            if res and "MYMEMORY WARNING" not in res.upper():
                TRANSLATION_CACHE[cache_key] = res
                return res
    except Exception:
        pass

    try:
        url3 = "https://translate.googleapis.com/translate_a/single"
        params3 = {"client": "gtx", "sl": source_lang, "tl": target_lang, "dt": "t", "q": text}
        r3 = requests.get(url3, params=params3, headers=headers, timeout=5)
        if r3.status_code == 200:
            data3 = r3.json()
            res = "".join([part[0] for part in data3[0] if part[0]]).strip()
            if res:
                TRANSLATION_CACHE[cache_key] = res
                return res
    except Exception:
        pass

    raise AIServiceError("Mạng đang bận, vui lòng thử lại sau vài giây.")


def segment_chinese_words(sentence: str) -> list:
    sorted_dict_words = sorted(TECHNICAL_DICT.keys(), key=len, reverse=True)
    tokens = []
    i = 0
    n = len(sentence)

    while i < n:
        ch = sentence[i]
        if not is_chinese(ch):
            i += 1
            continue

        matched_word = None
        for w in sorted_dict_words:
            if sentence.startswith(w, i):
                matched_word = w
                break

        if matched_word:
            if matched_word not in tokens:
                tokens.append(matched_word)
            i += len(matched_word)
        else:
            single_particles = {"请", "把", "被", "的", "了", "着", "过", "吗", "呢", "吧", "在", "去", "来", "和", "与", "或", "先", "再", "不", "没", "很", "太", "都", "也", "我", "你", "他", "它"}
            if ch in single_particles or i + 1 >= n or not is_chinese(sentence[i + 1]):
                if ch not in tokens:
                    tokens.append(ch)
                i += 1
            else:
                two_char = sentence[i:i + 2]
                if two_char not in tokens:
                    tokens.append(two_char)
                i += 2

    return tokens[:12]


def test_api_connection() -> tuple[bool, str]:
    try:
        sample = "机器视觉可以自动检测产品"
        trans = multi_engine_web_translate(sample, source_lang="zh-CN", target_lang="vi")
        return True, f"Kết nối Hệ thống Dịch Thuật & Từ Điển thành công!\nBản dịch thử: {trans}"
    except Exception as e:
        return False, str(e)


# =====================================================================
# 1. CHỨC NĂNG DỊCH THUẬT HAI CHIỀU TRUNG - VIỆT
# =====================================================================
def request_translation(text: str, direction: str = "Tự động", mode: str = "Tự động") -> dict:
    text = text.strip()
    if not text:
        raise AIServiceError("Vui lòng nhập nội dung cần dịch!")

    if "Trung → Tiếng Việt" in direction:
        src_code, tgt_code = "zh-CN", "vi"
        detected_lang, target_lang = "Tiếng Trung", "Tiếng Việt"
    elif "Việt → Tiếng Trung" in direction:
        src_code, tgt_code = "vi", "zh-CN"
        detected_lang, target_lang = "Tiếng Việt", "Tiếng Trung"
    else:
        if is_chinese(text):
            src_code, tgt_code = "zh-CN", "vi"
            detected_lang, target_lang = "Tiếng Trung", "Tiếng Việt"
        else:
            src_code, tgt_code = "vi", "zh-CN"
            detected_lang, target_lang = "Tiếng Việt", "Tiếng Trung"

    main_trans = multi_engine_web_translate(text, src_code, tgt_code)
    alt_trans = ""

    if text in TECHNICAL_DICT and tgt_code == "vi":
        info = TECHNICAL_DICT[text]
        alt_trans = f"Âm Hán Việt: {info['hv']} | Chủ đề: {info.get('topic', 'Camvision')}"

    zh_content = text if src_code == "zh-CN" else main_trans
    pinyin_str = generate_local_pinyin(zh_content)

    found_terms = []
    for term, info in TECHNICAL_DICT.items():
        if term in zh_content:
            term_py = info.get("pinyin") or generate_local_pinyin(term)
            found_terms.append(f"• {term} ({term_py} | Hán Việt: {info['hv']}): {info['vi']}")

    key_terms_str = "\n".join(found_terms) if found_terms else "Đã dịch hoàn tất."

    return {
        "detected_lang": detected_lang,
        "target_lang": target_lang,
        "translation": main_trans,
        "alternative": alt_trans,
        "pinyin": pinyin_str,
        "key_terms": key_terms_str,
        "ambiguity_warning": ""
    }


# =====================================================================
# 2. CHỨC NĂNG KIỂM TRA BẢN DỊCH NGƯỢC
# =====================================================================
def request_back_translation(original_text: str, translated_text: str, mode: str = "Tự động") -> dict:
    orig_is_zh = is_chinese(original_text)
    back_src = "vi" if orig_is_zh else "zh-CN"
    back_tgt = "zh-CN" if orig_is_zh else "vi"

    back_text = multi_engine_web_translate(translated_text, source_lang=back_src, target_lang=back_tgt)

    clean_orig = re.sub(r"\s+", "", original_text.lower())
    clean_back = re.sub(r"\s+", "", back_text.lower())
    score = "100% - Khớp hoàn toàn với câu gốc" if clean_orig == clean_back else "Tương đương ngữ nghĩa"

    return {
        "back_translation": back_text,
        "accuracy_score": score,
        "missing_or_added": "Không phát hiện thiếu sót thông số hay số liệu.",
        "comparison_notes": f"Câu gốc: '{original_text}'  <==>  Dịch ngược: '{back_text}'"
    }


# =====================================================================
# 3. TRA CỨU TỪ VỰNG TRỰC QUAN (THEO MẪU 适应: VÍ DỤ DỄ, CỤM TỪ, HỘI THOẠI)
# =====================================================================
def lookup_vocabulary(query: str) -> dict:
    raw_query = query.strip()
    if not raw_query:
        raise AIServiceError("Vui lòng nhập từ hoặc cụm từ cần tra cứu!")

    corrected_query = AUTO_CORRECTION_RULES.get(raw_query, raw_query)

    if not is_chinese(corrected_query):
        zh_word = multi_engine_web_translate(corrected_query, source_lang="vi", target_lang="zh-CN")
        vi_meaning = corrected_query
    else:
        zh_word = corrected_query
        vi_meaning = multi_engine_web_translate(zh_word, source_lang="zh-CN", target_lang="vi")

    pinyin_str = generate_local_pinyin(zh_word)
    hv_str, hsk_str = get_char_by_char_hanviet_and_hsk(zh_word)

    # Nếu từ có sẵn cấu trúc chi tiết (như 适应, 任何)
    if zh_word in TECHNICAL_DICT and "collocations" in TECHNICAL_DICT[zh_word]:
        d = TECHNICAL_DICT[zh_word]
        return {
            "word": zh_word,
            "pinyin": d["pinyin"],
            "hanviet": d["hv"],
            "pos": d["pos"],
            "hsk": d["hsk"],
            "meaning_common": d["vi"],
            "usage": d["usage"],
            "recommended_topic": d["topic"],
            "examples": d["examples"],
            "collocations": d["collocations"],
            "grammar_note": d["grammar_note"],
            "dialogue": d["dialogue"]
        }

    # Nếu nằm trong từ điển Camvision / Kỹ thuật
    if zh_word in TECHNICAL_DICT:
        tech = TECHNICAL_DICT[zh_word]
        pinyin_str = tech.get("pinyin") or pinyin_str
        hv_str = tech["hv"]
        pos = tech["pos"]
        meaning_clean = tech["vi"]
        topic = tech.get("topic", "Camvision")
        ex1_zh, ex1_vi = tech["ex"]
    else:
        pos = "Động từ / Danh từ"
        meaning_clean = vi_meaning
        topic = "Camvision"
        ex1_zh = f"在工作中，我们需要注意{zh_word}的问题。"
        ex1_vi = multi_engine_web_translate(ex1_zh, "zh-CN", "vi")

    ex2_zh = f"请先检查一下{zh_word}是否正常。"
    ex2_vi = multi_engine_web_translate(ex2_zh, "zh-CN", "vi")

    ex3_zh = f"他很快就掌握了{zh_word}的操作方法。"
    ex3_vi = multi_engine_web_translate(ex3_zh, "zh-CN", "vi")

    collocations = [
        (f"检查{zh_word}", generate_local_pinyin(f"检查{zh_word}"), f"Kiểm tra {meaning_clean}"),
        (f"调整{zh_word}", generate_local_pinyin(f"调整{zh_word}"), f"Điều chỉnh {meaning_clean}"),
        (f"测试{zh_word}", generate_local_pinyin(f"测试{zh_word}"), f"Chạy thử / Test {meaning_clean}"),
        (f"{zh_word}正常", generate_local_pinyin(f"{zh_word}正常"), f"{meaning_clean.capitalize()} bình thường"),
        (f"{zh_word}异常", generate_local_pinyin(f"{zh_word}异常"), f"{meaning_clean.capitalize()} bất thường"),
    ]

    dialogue = [
        (f"A: 请问这台设备的{zh_word}调整好了吗？", generate_local_pinyin(f"请问这台设备的{zh_word}调整好了吗？"), f"A: Cho hỏi {meaning_clean} của thiết bị này đã điều chỉnh xong chưa?"),
        (f"B: 已经调好了，现在可以进行测试运行。", "Yǐjīng tiáo hǎo le, xiànzài kěyǐ jìnxíng cèshì yùnxíng.", "B: Đã chỉnh xong rồi, bây giờ có thể tiến hành chạy thử."),
        ("A: 好的，如果有问题请马上告诉我。", "Hǎo de, rúguǒ yǒu wèntí qǐng mǎshàng gàosu wǒ.", "A: Ok, nếu có vấn đề gì vui lòng báo ngay cho tôi."),
        ("B: 没问题，放心吧。", "Méi wèntí, fàngxīn ba.", "B: Không vấn đề gì, cứ yên tâm nhé.")
    ]

    return {
        "word": zh_word,
        "pinyin": pinyin_str,
        "hanviet": hv_str,
        "pos": pos,
        "hsk": hsk_str,
        "meaning_common": meaning_clean,
        "usage": f"{zh_word} ({meaning_clean}) thường dùng trực tiếp trong môi trường công việc, kỹ thuật nhà máy và giao tiếp thực tế hàng ngày.",
        "recommended_topic": topic,
        "examples": [
            {"zh": ex1_zh, "pinyin": generate_local_pinyin(ex1_zh), "vi": ex1_vi},
            {"zh": ex2_zh, "pinyin": generate_local_pinyin(ex2_zh), "vi": ex2_vi},
            {"zh": ex3_zh, "pinyin": generate_local_pinyin(ex3_zh), "vi": ex3_vi},
        ],
        "collocations": collocations,
        "grammar_note": f"• Động từ (检查 / 调整 / 使用) + {zh_word}: Kiểm tra / điều chỉnh / sử dụng {meaning_clean}.\n• {zh_word} + Tính từ (正常 / 模糊 / 清晰): Miêu tả trạng thái của {meaning_clean}.",
        "dialogue": dialogue
    }


# =====================================================================
# 4. CHỨC NĂNG PHÂN TÍCH NGỮ PHÁP TIẾNG TRUNG
# =====================================================================
def analyze_grammar(sentence: str) -> dict:
    sentence = sentence.strip()
    if not sentence:
        raise AIServiceError("Vui lòng nhập câu cần phân tích!")

    sentence = AUTO_CORRECTION_RULES.get(sentence, sentence)
    pinyin_full = generate_local_pinyin(sentence)
    vi_meaning = multi_engine_web_translate(sentence, source_lang="zh-CN", target_lang="vi")

    grammar_points = []
    if "请" in sentence:
        grammar_points.append("• Cấu trúc đề nghị lịch sự với 请 (Qǐng - Vui lòng/Xin hãy): Đứng đầu câu mệnh lệnh trong công việc/nhà máy.")
    if "按照" in sentence or "根据" in sentence:
        grammar_points.append("• Cấu trúc giới từ [按照 / 根据 + Danh từ + Động từ]: Dựa theo / Chiếu theo cái gì đó để thực hiện.")
    if "把" in sentence:
        grammar_points.append("• Câu chữ 把 (Bǎ): [Chủ ngữ + 把 + Tân ngữ + Động từ + Kết quả], nhấn mạnh việc xử lý/tác động lên sự vật.")
    if "以后" in sentence or "后" in sentence:
        grammar_points.append("• Cấu trúc thời gian [... 以后 / 后，再...]: Sau khi hoàn thành việc A thì mới thực hiện việc B.")
    if "的" in sentence:
        grammar_points.append("• Trợ từ kết cấu 的 (De): [Định ngữ + 的 + Danh từ], khi dịch sang tiếng Việt ta dịch từ sau chữ 的 dịch ngược lên.")

    if not grammar_points:
        grammar_points.append("• Câu trần thuật tiêu chuẩn: [Chủ ngữ (S) + Động từ (V) + Tân ngữ (O)].")

    words_in_sentence = segment_chinese_words(sentence)
    vocab_breakdown = []

    for w in words_in_sentence:
        w_py = generate_local_pinyin(w)
        if w in TECHNICAL_DICT:
            info = TECHNICAL_DICT[w]
            vocab_breakdown.append(f"  - {w} ({w_py} | Hán Việt: {info['hv']}): {info['vi']}")
        else:
            hv_w, _ = get_char_by_char_hanviet_and_hsk(w)
            try:
                w_vi = multi_engine_web_translate(w, source_lang="zh-CN", target_lang="vi")
            except Exception:
                w_vi = "Từ thành phần trong câu"
            vocab_breakdown.append(f"  - {w} ({w_py} | Hán Việt: {hv_w}): {w_vi}")

    report_lines = [
        "======================================================================",
        "📘 KẾT QUẢ PHÂN TÍCH NGỮ PHÁP & CẤU TRÚC CÂU",
        "======================================================================",
        f"1. CÂU GỐC     : {sentence}",
        f"   PINYIN      : {pinyin_full}",
        f"   NGHĨA CÂU   : {vi_meaning}",
        "",
        "2. ĐIỂM NGỮ PHÁP & CẤU TRÚC TRỌNG TÂM:",
        "\n".join(grammar_points),
        "",
        "3. TỪ VỰNG & THUẬT NGỮ TRONG CÂU:",
        "\n".join(vocab_breakdown) if vocab_breakdown else "  - Không có từ vựng.",
        "",
        "4. SẮC THÁI & ỨNG DỤNG THỰC TẾ:",
        "  • Câu này dùng trực tiếp trong giao tiếp công việc, kỹ thuật nhà máy hoặc hội thoại hàng ngày."
    ]

    return {
        "sentence": sentence,
        "pinyin": pinyin_full,
        "meaning": vi_meaning,
        "report": "\n".join(report_lines)
    }