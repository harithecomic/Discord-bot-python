import logging

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("event-bot-logs.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("discord_bot")

logger = setup_logger()