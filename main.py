from loguru import logger
import urllib3
import sys
import os
import asyncio

# try to import granular runners; fall back to start()
try:
    from process import start, run_ai_chatter, run_message_sender
except ImportError:
    from process import start
    run_ai_chatter = None
    run_message_sender = None

from dotenv import load_dotenv
load_dotenv(dotenv_path=".env", override=False)


def configuration():
    import os
    from pathlib import Path
    urllib3.disable_warnings()
    logger.remove()

    log_dir = os.getenv("LOG_DIR", r"D:\helpD-logs")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_retention = os.getenv("LOG_RETENTION", "14 days")
    log_json = os.getenv("LOG_JSON", "0") == "1"

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    task = (os.getenv("AUTORUN_TASK") or "-").upper()
    gid = os.getenv("AI_GUILD_ID") or os.getenv("SENDER_GUILD_ID") or "-"
    cid = os.getenv("AI_CHANNEL_ID") or os.getenv("SENDER_CHANNEL_ID") or "-"

    fmt = (
        "<light-cyan>{time:YYYY-MM-DD HH:mm:ss}</light-cyan> | "
        "<level>{level: <8}</level> | {name}:{line} | "
        f"[task={task} gid={gid} cid={cid}] - <bold>{{message}}</bold>"
    )

    # консоль
    logger.add(sys.stdout, colorize=True, format=fmt, level=log_level)

    # общий файл с ротацией/ретеншеном
    logger.add(
        Path(log_dir) / "helpd_{time:YYYYMMDD}.log",
        rotation="20 MB",
        retention=log_retention,
        compression="zip",
        level=log_level,
        enqueue=True,
        backtrace=True,
        diagnose=False,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | "
               f"[task={task} gid={gid} cid={cid}] - {{message}}",
    )

    # файл только для ошибок
    logger.add(
        Path(log_dir) / "errors_{time:YYYYMMDD}.log",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=False,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | "
               f"[task={task} gid={gid} cid={cid}] - {{message}}",
    )

    if log_json:
        logger.add(
            Path(log_dir) / "json_{time:YYYYMMDD}.log",
            serialize=True,
            rotation="20 MB",
            retention=log_retention,
            compression="zip",
            level=log_level,
            enqueue=True,
        )


async def main():
    configuration()

    # AUTORUN (skip menu)
    autorun = os.getenv("AUTORUN", "")
    if autorun:
        task = (os.getenv("AUTORUN_TASK", "") or "").upper().strip()
        if task == "MESSAGE_SENDER" and callable(run_message_sender):
            logger.info("Autorun: MESSAGE_SENDER")
            await run_message_sender()
            return
        elif task == "AI_CHATTER" and callable(run_ai_chatter):
            logger.info("Autorun: AI_CHATTER")
            await run_ai_chatter()
            return
        logger.info("Autorun requested, delegating to process.start()")
        await start()
        return

    # default path with menu inside process.start()
    await start()


if __name__ == "__main__":
    asyncio.run(main())
