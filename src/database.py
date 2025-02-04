# src/database.py

import mysql.connector
from mysql.connector import Error
from config import Config
import logging
import pymysql
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

class Database:
    def __init__(self):
        logging.debug("Inicializando la clase Database.")
        self.host = Config.MYSQL_HOST
        self.port = Config.MYSQL_PORT
        self.user = Config.MYSQL_USER
        self.password = Config.MYSQL_PASSWORD
        self.database = Config.MYSQL_DB
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if self.connection.is_connected():
                logging.info("Conexión a la base de datos MySQL exitosa")
        except Error as e:
            logging.error(f"Error al conectar a la base de datos: {e}")
            self.connection = None

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logging.info("Conexión a la base de datos MySQL cerrada")

    def check_and_reconnect(self):
        """Verifica si la conexión está activa y la restablece si es necesario."""
        try:
            if self.connection is None or not self.connection.is_connected():
                logging.info("Reconectando a la base de datos...")
                self.connect()  # Intentar reconectar
            else:
                self.connection.ping(reconnect=True)  # Intentar hacer un ping a la base de datos
        except Error as e:
            logging.error(f"Error al verificar o reconectar la base de datos: {e}")
            self.disconnect()  # Si ocurre un error, cerramos la conexión y tratamos de reconectar
            self.connect()

    def execute_query(self, query, params=None):
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except Error as e:
            logging.error(f"Error al ejecutar la consulta: {e}")
            return None
        finally:
            cursor.close()

    def execute_proc(self, proc_name, params):
        cursor = self.connection.cursor()
        try:
            cursor.callproc(proc_name, params)
            logging.info(f"Procedimiento almacenado {proc_name} ejecutado con éxito.")
        except Error as e:
            logging.error(f"Error al ejecutar el procedimiento almacenado {proc_name}: {e}")
        finally:
            cursor.close()

    def commit(self):
        if self.connection:
            self.connection.commit()
            logging.debug("Cambios en la base de datos confirmados.")