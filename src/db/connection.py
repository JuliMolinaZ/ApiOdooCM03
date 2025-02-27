# src/db/connection.py
# Establece la conexion con la bae de datos.

import logging
import mysql.connector
from mysql.connector import Error
from config.settings import Config

class DatabaseConnection:
    def __init__(self):
        logging.debug("Inicializando la clase DatabaseConnection.")
        self.host = Config.MYSQL_HOST
        self.port = Config.MYSQL_PORT
        self.user = Config.MYSQL_USER
        self.password = Config.MYSQL_PASSWORD
        self.database = Config.MYSQL_DB
        self.connection = None

    def connect(self):
        """Establece la conexion con la base de datos"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if self.connection.is_connected():
                logging.info("Conexion a la base de datos MySQL existosa.")
        except Error as e:
                logging.error(f"Error al conectar a la base de datos: {e}")
                self.connection = None

    def disconnect(self):
        """Cierra la conexion con la base de datos"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logging.info("Conexion a la base de datos MySQL cerrada.")

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