import logging

def setup_logger():
    """
    Sets up the logger for the bot.
    Logs to console with INFO level.
    """
    logger = logging.getLogger("discord_bot")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
    handler.setFormatter(formatter)

    if not logger.hasHandlers():
        logger.addHandler(handler)

    return logger
