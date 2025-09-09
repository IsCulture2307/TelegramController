import logging
import os

from telethon import TelegramClient, errors
from utils.config import API_ID, API_HASH
from utils.helpers import app_path


async def send_message_to_chats(session_name, chat_ids, message_text):
    session_folder = app_path("session")
    session_file = os.path.join(session_folder, f"{session_name}.session")
    client = TelegramClient(session_file, API_ID, API_HASH)
    sent_ids = []  # 用于记录成功发送的ID
    try:
        await client.start()
        for chat_id in chat_ids:
            try:
                await client.send_message(chat_id, message_text)
                logging.info(f"✅ ({session_name}) 已发送到 {chat_id}")
                sent_ids.append(chat_id)  # 记录成功
            except Exception as e:
                logging.error(f"❌ ({session_name}) 发送到 {chat_id} 失败: {e}")
        # **关键修改：返回成功发送的 ID 列表**
        return True, "发送成功", sent_ids
    except Exception as e:
        logging.error(f"❌ ({session_name}) Telegram 客户端操作失败: {e}")
        return False, f"Telegram 客户端操作失败: {e}", []
    finally:
        if client.is_connected():
            await client.disconnect()


async def get_group_ids_and_names(session_name):
    session_file = os.path.join("session", f"{session_name}.session")
    client = TelegramClient(session_file, API_ID, API_HASH)
    try:
        await client.start()
        dialogs = await client.get_dialogs()
        group_data = [(d.id, d.title) for d in dialogs if d.is_group or d.is_channel]
        logging.info(f"✅ ({session_name}) 成功获取 {len(group_data)} 个群组/频道")
        return group_data, None
    except errors.SessionPasswordNeededError:
        error_msg = f"账号 '{session_name}' 需要两步验证密码"
        logging.error(f"❌ {error_msg}")
        return None, error_msg
    except Exception as e:
        error_msg = f"获取群组列表失败: {e}"
        logging.error(f"❌ ({session_name}) {error_msg}")
        return None, error_msg
    finally:
        if client.is_connected():
            await client.disconnect()