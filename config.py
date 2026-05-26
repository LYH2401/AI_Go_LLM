
"""
AI_Go_LLM - 全局路径配置
所有路径统一从此文件引用，禁止在业务代码中硬编码！
"""

import os
from pathlib import Path
from dotenv import load_dotenv


# ----- 项目根目录（自动检测）-----
PROJECT_ROOT = Path(__file__).parent.resolve()
# ----- 数据目录 -----
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
SGF_DIR = DATA_DIR / "sgf"            # 原始 SGF 棋谱
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)  # 自动创建
# ----- KataGo 配置 -----
KATAGO_PATH = os.getenv("KATAGO_PATH", "katago")
KATAGO_MODEL = os.getenv("KATAGO_MODEL", "")
KATAGO_CONFIG = os.getenv("KATAGO_CONFIG", "")
# ----- 模型 API -----
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
# ===== 使用示例 =====
if __name__ == "__main__":
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"数据目录:   {DATA_DIR}")
    print(f"输出目录:   {OUTPUT_DIR}")