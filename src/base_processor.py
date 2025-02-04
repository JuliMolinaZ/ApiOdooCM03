# src/base_processor.py

from odoo_client import OdooClient
from database import Database
import logging

class BaseProcessor:
    def __init__(self):
        logging.info("Inicializando BaseProcessor")
        self.odoo = OdooClient()
        self.db = Database()
        self.db.connect()

    def close_connections(self):
        logging.info("Cerrando conexiones en BaseProcessor")
        self.db.disconnect()

    def run(self):
        raise NotImplementedError("Debe implementar el método run en la subclase")