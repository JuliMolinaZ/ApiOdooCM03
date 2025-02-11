# src/config/settings.py

from dotenv import load_dotenv
import os

# Cargar variables de entorno desde el archivo .env ubicado en el directorio raíz del proyecto
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    # Configuraciones de Odoo
    ODOO_URL = os.getenv('ODOO_URL')
    ODOO_DB = os.getenv('ODOO_DB')
    ODOO_USERNAME = os.getenv('ODOO_USERNAME')
    ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

    # Configuraciones de MySQL
    MYSQL_HOST = os.getenv('MYSQL_HOST')
    MYSQL_PORT = os.getenv('MYSQL_PORT')
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_DB = os.getenv('MYSQL_DB')