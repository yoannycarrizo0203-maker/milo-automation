import logging
import json
import os
import sys
from datetime import datetime
from execution.config import LOG_PATH

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
        }
        if hasattr(record, "props"):
            log_record.update(record.props)
        return json.dumps(log_record)

def setup_logger(name="MILO"):
    # Ensure log dir exists
    log_dir = os.path.dirname(LOG_PATH)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # File Handler (JSON)
    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    # Console Handler (Human Friendly)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    return logger

logger = setup_logger()
