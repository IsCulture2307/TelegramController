import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.config import config, DEFAULT_ACCOUNT_CONFIG
from core.telegram import send_message_to_chats

scheduler = AsyncIOScheduler()

def initialize_scheduler(loop=None):
    """启动调度器"""
    try:
        # 如果 scheduler 实例还没有被赋予 event_loop，在这里赋予它
        if not getattr(scheduler, 'event_loop', None) and loop:
            scheduler.configure(event_loop=loop)

        if not scheduler.running:
            scheduler.start()
            logging.info("🕒 后台定时任务调度器已启动")
    except Exception as e:
        logging.error(f"❌ 启动调度器失败: {e}")

def shutdown_scheduler():
    """安全关闭调度器"""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logging.info("🕒 后台定时任务调度器已关闭")
    except Exception as e:
        logging.error(f"❌ 关闭调度器失败: {e}")

async def update_or_create_schedule(session_name: str):
    """
    根据最新配置，为指定账号更新或创建定时发送任务。
    """
    account_config = config["accounts"].get(session_name, DEFAULT_ACCOUNT_CONFIG)
    target_ids = [int(k) for k in account_config.get("target_chats", {}).keys()]
    target_chats_map = {int(k): v for k, v in account_config.get("target_chats", {}).items()}
    job_id = f"daily_send_{session_name}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    if target_ids:
        async def scheduled_send_wrapper():
            logging.info(f"⏰ 定时任务触发: ({session_name})")
            await send_message_to_chats(session_name, target_ids, account_config["message_text"], target_chats_map)

        scheduler.add_job(
            scheduled_send_wrapper,
            "cron",
            hour=account_config["send_hour"],
            minute=account_config["send_minute"],
            id=job_id
        )
        logging.info(f"🕒 ({session_name}) 定时任务已更新为 {account_config['send_hour']}:{account_config['send_minute']:02d}")
    else:
        logging.info(f"🕒 ({session_name}) 没有发送目标，定时任务未设置")