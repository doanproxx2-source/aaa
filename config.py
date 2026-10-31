import os
from pathlib import Path
from dotenv import load_dotenv, set_key

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)


class Config:
    APP_NAME = "CHINESE – VIETNAMESE TRANSLATOR PRO"
    APP_SUBTITLE = "中越智能翻译助手 – Phần mềm dịch thuật Trung Việt thông minh"

    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY",
        "AQ.Ab8RN6KdsGkphvm8snlf0-cqFbhzOJW0CtgWFkUr3p1L6SVyrg"
    ).strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

    AVAILABLE_MODELS = [
        "gemini-3.8-flash",
        "gemini-3.8-pro",
        "gemini-2.5-flash",
        "gemini-2.5-pro"
    ]

    TRANSLATION_MODES = [
        "Tự động",
        "Giao tiếp hàng ngày",
        "Giao tiếp công việc",
        "Văn bản chuyên nghiệp",
        "Văn bản trang trọng",
        "Dịch chuyên ngành kỹ thuật",
        "Dịch tài liệu máy móc",
        "Dịch email và thông báo công ty"
    ]

    # Chỉ giữ lại chủ đề gốc Camvision, người dùng tự thêm hoặc nhập từ Excel
    VOCAB_TOPICS = [
        "Camvision"
    ]

    @classmethod
    def save_settings(cls, api_key: str, model: str):
        cls.GEMINI_API_KEY = api_key.strip()
        cls.GEMINI_MODEL = model.strip()
        if not ENV_PATH.exists():
            ENV_PATH.touch()
        set_key(str(ENV_PATH), "GEMINI_API_KEY", cls.GEMINI_API_KEY)
        set_key(str(ENV_PATH), "GEMINI_MODEL", cls.GEMINI_MODEL)