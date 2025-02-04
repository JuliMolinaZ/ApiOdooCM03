# src/logging_config.py
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    log_handler = RotatingFileHandler("app.log", maxBytes=5 * 1024 * 1024, backupCount=3)
    logging.basicConfig(handlers=[log_handler], level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Logging configurado correctamente.")
