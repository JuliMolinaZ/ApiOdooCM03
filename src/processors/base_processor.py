# src/processors/base_processor.py

from api.odoo_client import OdooClient
from db.connection import DatabaseConnection
import logging

class BaseProcessor:
    def __init__(self):
        logging.info("Inicializando BaseProcessor")
        
        # Inicializar conexion con la base de datos y Odoo
        self.db = DatabaseConnection()
        self.odoo = OdooClient()

        # Conectar a la base de datos
        self.db.connect()

    def close_connections(self):
        logging.info("Cerrando conexiones en BaseProcessor")
        self.db.disconnect()
    
    def run(self):
        raise NotImplementedError("Debe implementar el metodo run en la subclase")