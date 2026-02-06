import logging
from logging.handlers import RotatingFileHandler
from config.settings import LOG_FILE

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3),
            logging.StreamHandler()
        ]
    )

setup_logging()
