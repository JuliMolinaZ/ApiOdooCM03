# src/api/client.py
# Conexion a Odoo, consultas o acciones relacionadas.

import xmlrpc.client
from config.settings import Config
import logging

class OdooClient:
    def __init__(self):
        self.url = Config.ODOO_URL
        self.db = Config.ODOO_DB
        self.username = Config.ODOO_USERNAME
        self.password = Config.ODOO_PASSWORD
        self.uid = None
        self.models = None
        self.connect()

    def connect(self):
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if self.uid:
                self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
                logging.info(f"Conexión a Odoo exitosa, UID: {self.uid}")
            else:
                logging.error("Falló la autenticación en Odoo")
        except Exception as e:
            logging.error(f"Error al conectar a Odoo: {e}")

    def execute_kw(self, model, method, args, kwargs=None):
        if not kwargs:
            kwargs = {}
        try:
            return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs)
        except Exception as e:
            logging.error(f"Error al ejecutar {method} en {model}: {e}")
            return None
        
    def search(self, model, domain):
        return self.execute_kw(model, 'search', [domain])
    
    def read(self, model, ids, fields):
        """ Lee registros de un modelo en Odoo. """
        return self.models.execute_kw(self.db, self.uid, self.password,
                                    model, 'read', [ids], {'fields': fields})

