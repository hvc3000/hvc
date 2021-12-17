import sys
import logging
from logging.handlers import WatchedFileHandler, TimedRotatingFileHandler

def get_logger(stdout: bool = False):
    logger = logging.getLogger("bpow")
    logging.basicConfig(level=logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s@%(funcName)s:%(lineno)s:%(message)s", "%Y-%m-%d %H:%M:%S %z")
    if not stdout:
        log_file = "/tmp/bpow.log"
        handler = WatchedFileHandler(log_file)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.addHandler(TimedRotatingFileHandler(log_file, when="d", interval=1, backupCount=100))
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
