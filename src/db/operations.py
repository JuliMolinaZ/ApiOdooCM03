# src/db/operations.py
# Operaciones (consultas, actualizaciones, etc) sobre la base de datos

from db.connection import DatabaseConnection
from mysql.connector import Error
import logging
from datetime import datetime

class DatabaseOperations:
    def __init__(self):
        self.db_connection = DatabaseConnection()
        self.db_connection.connect()

    def execute(self, query, params=None, proc=False):
        """Ejecuta consultas SQL o procedimientos almacenados en la base de datos."""
        cursor = self.db_connection.connection.cursor(dictionary=True)
        try:
            #logging.info(f"Ejecutando consulta: {query} con parámetros: {params}")
            if proc:
                # Ejecuta un procedimiento almacenado
                cursor.callproc(query, params)
                for result in cursor.stored_results():
                    logging.info(f"Procedimiento almacenado {query} ejecutado con éxito.")
            else:
                # Ejecuta una consulta SQL
                cursor.execute(query, params)
                result = cursor.fetchall()  # Si es una consulta, devuelve los resultados
                #logging.info(f"Consulta SQL ejecutada correctamente, resultados obtenidos: {result}")
                return result
            self.db_connection.connection.commit()  # Confirma la transacción
        except Error as e:
            logging.error(f"Error ejecutando la operación: {e}")
            return None
        finally:
            cursor.close()
            
# Para albaranes_processor.py
    def verificar_albaran_procesado(self, albaran_id):
        """Verifica si el albarán ya ha sido procesado."""
        try:
            result = self.execute("SELECT Procesado FROM Albaran WHERE AlbaranID = %s", (albaran_id,))
            if result:
                return result[0]['Procesado'] == 1  # Si el albarán está marcado como procesado
            return False
        except Exception as e:
            logging.error(f"Error verificando albarán procesado: {e}")
            return False

    def insertar_o_actualizar_albaran(self, albaran_id, fecha_creacion, cliente, albaran_folio):
        """Llama al procedimiento almacenado para insertar o actualizar un albarán."""
        try:
            logging.info(f"Parámetros para InsertOrUpdateAlbaranTest: {(
                albaran_id, fecha_creacion, cliente, albaran_folio,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Pendiente', None, None, 0.0, '2024-01-01', None
            )}")
            self.execute('InsertOrUpdateAlbaranTest', (
                albaran_id, fecha_creacion, cliente, albaran_folio,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Pendiente', None, None, 0.0, '2024-01-01', None
            ), proc=True)
            logging.info(f"Albarán {albaran_folio} insertado o actualizado en la base de datos.")
        except Exception as e:
            logging.error(f"Error insertando o actualizando albarán {albaran_folio}: {e}")

    def insertar_detalle_albaran(self, linea_id, albaran_id, product_id, quantity, location_dest):
        """Inserta detalles de albarán en la base de datos."""
        try:
            self.execute('InsertOrUpdateAlbaranDetalle', (
                linea_id, albaran_id, product_id, quantity, 0.0,
                None, location_dest, None, None
            ), proc=True)
            logging.info(f"Insertando/Actualizando detalle del albarán {albaran_id} con parámetros: {linea_id}, {product_id}, Cantidad={quantity}, Destino={location_dest}")
            logging.info(f"Detalle del albarán {albaran_id} insertado correctamente.")
        except Exception as e:
            logging.error(f"Error insertando detalle del albarán {albaran_id}: {e}")

    def marcar_albaran_como_procesado(self, albaran_id):
        """Marca el albarán como procesado en la base de datos."""
        try:
            self.execute("UPDATE Albaran SET Procesado = 1 WHERE AlbaranID = %s", (albaran_id,))
            self.db_connection.connection.commit()
            logging.info(f"Albarán {albaran_id} marcado como procesado.")
        except Exception as e:
            logging.error(f"Error al marcar el albarán {albaran_id} como procesado: {e}")

    def close(self):
        """Cierra la conexión con la base de datos."""
        if self.db_connection.connection and self.db_connection.connection.is_connected():
            self.db_connection.connection.close()  # Cierra la conexión
            logging.info("Conexión cerrada exitosamente.")
        else:
            logging.warning("No se pudo cerrar la conexión: No está conectada.")

# Para recibos_processor.py
    def verificar_recibo_procesado(self, recibo_id):
        """Verifica si el recibo ya ha sido procesado."""
        try:
            procesado = self.execute("SELECT COUNT(*) FROM Recibos WHERE ReciboID = %s", (recibo_id,))
            if procesado[0]['COUNT(*)'] > 0:
                logging.info(f"El reciboID: {recibo_id} ya existe en la base de datos. Saltando procesamiento")  # Si el albarán está marcado como procesado
                return True
            return False
        except Exception as e:
            logging.error(f"Error verificando albarán procesado: {e}")

    def insertar_o_actualizar_recibo(self, recibo_id, fecha_creacion, partner_name, recibo_data):
        """Inserta o Actualiza el recibo en la base de datos"""
        try:
            self.execute('InsertOrUpdateRecibo', (
                recibo_id, fecha_creacion, partner_name, recibo_data['name'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Pendiente', None, None, 0.0, '2024-01-01', None
            ), proc=True)
        except Exception as e:
            logging.error(f"Error insertando recibo {recibo_id}: {e}")

    def insertar_detalle_recibo(self, linea_id, recibo_id, product_id, cantidad):
        """Inserta o Actualiza detalles del recibo en la base de datos"""
        try:
            self.execute('InsertOrUpdateReciboDetalle', (
                linea_id, recibo_id, product_id, cantidad, None
            ), proc=True)
        except Exception as e:
            logging.error(f"Error insertando detalle del recibo {recibo_id}: {e}")

# Para stock_cedis_processor.py
    def sku_en_bd(self, sku_actual):
        """Verifica si el producto con el SKU proporcionado ya existe en la base de datos."""
        try:
            result = self.execute("SELECT ProductoID FROM Productos WHERE ProductoSKUActual = %s", (sku_actual,))
            return len(result) > 0  # Verificar si hay resultados
        except Exception as e:
            logging.error(f"Error al verificar existencia de producto: {e}")
            return False
  
    def actualizar_producto(self, producto_id, producto_nombre, stock_total, stock_qra, stock_cdmx, sku_actual):
        """Actualiza la información del producto en la base de datos."""
        try:
            query_update = """
                UPDATE Productos
                SET ProductoID = %s, ProductoNombre = %s, ProductoStock = %s, StockQra = %s, StockCDMX = %s
                WHERE ProductoSKUActual = %s
            """
            self.execute(query_update, (producto_id, producto_nombre, stock_total, stock_qra, stock_cdmx, sku_actual))
            self.db_connection.connection.commit()
            logging.info(f"Producto actualizado en la BD: SKU={sku_actual}, StockTotal={stock_total}, StockQra={stock_qra}, StockCDMX={stock_cdmx}")
        except Exception as e:
            logging.error(f"Error al actualizar producto en la base de datos: {e}")
        
    def insertar_producto(self, producto_id, producto_nombre, sku_actual, stock_total, stock_qra, stock_cdmx):
        """Inserta un nuevo producto en la base de datos."""
        try:
            query_insert = """
                INSERT INTO Productos (ProductoID, ProductoNombre, ProductoSKUActual, ProductoStock, StockQra, StockCDMX)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            self.execute(query_insert, (producto_id, producto_nombre, sku_actual, stock_total, stock_qra, stock_cdmx))
            self.db_connection.connection.commit()
            logging.info(f"Producto insertado en la BD: ProductoID={producto_id}, SKU={sku_actual}, StockTotal={stock_total}, StockQro={stock_qra}, StockCDMX={stock_cdmx}")
        except Exception as e:
            logging.error(f"Error al insertar producto en la base de datos: {e}")

# Para stock_qro_processor.py
    def obtener_produc_existentes(self):
        try:
            logging.debug("Ejecutando consulta  de productos existentes en MySQL")
            query = "SELECT ProductoID, ProductoSKUActual, ProductoNombre, StockQra, StockCDMX FROM Productos"
            rows = self.execute(query)
            logging.debug("Productos obtenidos: %s", rows)
            return {row['ProductoID']: row for row in rows} if rows else {}
        except Exception as e:
            logging.error("Error al obtener productos existentes: %s", e)
            return {}
        
    def actualizar_produc_nombre(self, ProductoNombreOdoo, ProductoID):
        try:
            self.execute("UPDATE Productos SET ProductoNombre = %s WHERE ProductoID = %s", (ProductoNombreOdoo, ProductoID))
            self.db_connection.connection.commit()
        except Exception as e:
            logging.error("Error al obtener productos existentes: %s", e)
            return {}

    def actualizar_produc_stock(self, location_name, stock_new, ProductoID):
        try:
            self.execute(f"UPDATE Productos SET Stock{location_name} = %s WHERE ProductoID = %s", (stock_new, ProductoID))
            self.db_connection.connection.commit()
        except Exception as e:
            logging.error("Error al obtener productos existentes: %s", e)
            return {}
        
# Para tarimas_processor.py  
    def select_albaranes(self):
        try:
            return self.execute("SELECT AlbaranID FROM Albaran WHERE AlbaranStatus = 'Supervisado' AND ProcesoConcatenacionRealizado = 0 LIMIT 1000")
        except Exception as e:
            logging.error("Error al obtener albaranes existentes: %s", e)
            return {}
        
    def select_validaciones(self, albaran_id):
        try:
            return self.execute("SELECT ta.TarimaNumero, vt.ValidacionSKU, COUNT(*) AS CantidadValidaciones FROM ValidacionT vt JOIN TarimasA ta ON vt.TarimaID = ta.TarimaID WHERE vt.AlbaranID = %s GROUP BY ta.TarimaNumero, vt.ValidacionSKU", (albaran_id,))
        except Exception as e:
            logging.error("Error al obtener validaciones agrupadas: %s", e)
            return {}
        
    def select_producto(self, sku_actual):
        try:
            result = self.execute("SELECT ProductoID FROM Productos WHERE ProductoSKUActual = %s LIMIT 1", (sku_actual, ))
            return result[0] if result else None
        except Exception as e:
            logging.error("Error al obtener producto: %s", e)
            return {}
        
    def update_albarandetalle(self, concatenado, albaran_id, producto_id):
        try:
            self.execute("UPDATE AlbaranDetalle SET TarimasConcatenadas = %s WHERE AlbaranID = %s AND ProductoID = %s", (concatenado, albaran_id, producto_id, ))
            self.db_connection.connection.commit()
            logging.info(f"Actualizado AlbaranDetalle para ProductoID: {producto_id} con Tarimas: {concatenado}")
        except Exception as e:
            logging.error("Error al actualizar albaran detalle: %s", e)
            return {}
        
    def update_albaranstatus(self, albaran_id):
        try:
            self.execute("UPDATE Albaran SET ProcesoConcatenacionRealizado = 1 WHERE AlbaranID = %s", (albaran_id, ))
            self.db_connection.connection.commit()
            logging.info(f"AlbaranID {albaran_id} marcado como procesado.")
        except Exception as e:
            logging.error("Error al actualizar albaran como procesado: %s", e)
            return {}
