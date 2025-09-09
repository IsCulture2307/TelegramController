import json
import logging
import os

from utils.helpers import app_path

# ==== 全局常量和配置 ====
API_ID = 17349
API_HASH = "344583e45741c457fe1862106095a5eb"
CONFIG_FILE = app_path("config.json")
DEFAULT_ACCOUNT_CONFIG = {"target_chats": {}, "message_text": "这是自动群发的消息 ✅", "send_hour": 12, "send_minute": 23}
DEFAULT_CONFIG = {"accounts": {}, "window_width": 750, "window_height": 700}

# config 字典
config = {}

# ==== 读写配置 ====
def load_config():
    try:
        loaded_data = DEFAULT_CONFIG.copy()

        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                file_content = f.read().strip()
                if file_content:
                    loaded_data.update(json.loads(file_content))

        # 清空当前的 config 字典，并用加载好的数据填充它
        config.clear()
        config.update(loaded_data)

        logging.info("✅ config.json 已加载")

    except Exception as e:
        config.clear()
        config.update(DEFAULT_CONFIG.copy())
        logging.error(f"❌ 加载 config.json 时发生错误: {e}")


def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        logging.info("✅ 配置已保存")
    except Exception as e:
        logging.error(f"❌ 保存配置时发生错误: {e}")