# src/processors/stock_qra_processor.py
# Actualiza todos los productos existentes en la BD, considerando el stock de QRA y CDMX usando un diccionario de ubicaciones

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

import time
import msvcrt
import logging
from decimal import Decimal, ROUND_HALF_UP
from utils.logger import configurar_logger
from processors.base_processor import BaseProcessor
from api.odoo_operations import OdooOperations
from db.operations import DatabaseOperations

LOCK_FILE_PATH = 'sync_script.lock'
UBICACIONES = {
    'QRA': 8,  # ID de la ubicación WH/Stock QRA
    'CDMX': 38  # ID de la ubicación WH/Stock CDMX
}

class StockQroCM03(BaseProcessor):
    def __init__(self):
        super().__init__()
        logging.debug("Inicializado StockQroCM03")
        self.odoo_operations = OdooOperations(self.odoo)
        self.db_operations = DatabaseOperations()


    def obtener_productos_en_sububicaciones(self, location_id, offset=0, limit=100):
        """Obtiene productos en sububicaciones de una ubicación dada desde Odoo."""
        productos = self.odoo_operations.sububicaciones_produc_total(location_id, offset, limit)
        logging.debug("Productos obtenidos en Odoo para ubicación %s: %s", location_id, productos)
        return productos

    def obtener_nombres_productos(self, product_ids):
        """Obtiene los nombres de los productos en Odoo."""
        return self.odoo_operations.obtener_produc_total(product_ids)

    def obtener_productos_existentes(self):
        """Obtiene los productos existentes en MySQL."""
        return self.db_operations.obtener_produc_existentes()

    def actualizar_productos(self):
        existing_products = self.obtener_productos_existentes()
        if not existing_products:
            logging.warning("No se encontraron productos en MySQL")
            return

        offset = 0
        limit = 100
        product_quantities = {location: {} for location in UBICACIONES}
        product_sku_mapping = {}

        for location_name, location_id in UBICACIONES.items():
            logging.info("Obteniendo productos para la ubicación: %s (ID: %d)", location_name, location_id)
            while True:
                products = self.obtener_productos_en_sububicaciones(location_id, offset, limit)
                if not products:
                    break

                for product in products:
                    ProductoID = product['product_id'][0]
                    ProductoSKU = product['product_id'][1]
                    product_quantities[location_name][ProductoID] = product_quantities[location_name].get(ProductoID, 0) + product['quantity']
                    product_sku_mapping[ProductoID] = ProductoSKU
                    logging.debug("%s ProductoID %d: Cantidad acumulada = %s", location_name, ProductoID, product_quantities[location_name][ProductoID])

                offset += limit
            offset = 0  

        all_product_ids = set().union(*[quantities.keys() for quantities in product_quantities.values()])
        product_names, product_skus = self.obtener_nombres_productos(list(all_product_ids))
        total_actualizados = 0
        total_insertados = 0

        # diccionario vacío para almacenar el ProductoID más grande de cada SKU
        sku_max_id = {}
        for ProductoID in all_product_ids:
            ProductoSKUOdoo = product_skus.get(ProductoID, "")
            if ProductoSKUOdoo:
                if ProductoSKUOdoo not in sku_max_id or ProductoID > sku_max_id[ProductoSKUOdoo]: #almacena si es el primer id o si es mayor se reemplaza
                    sku_max_id[ProductoSKUOdoo] = ProductoID

        for ProductoID in all_product_ids:
            ProductoNombreOdoo = product_names.get(ProductoID, "")
            ProductoSKUOdoo = product_skus.get(ProductoID, "")
            
            if ProductoID not in existing_products:
                if ProductoID == sku_max_id.get(ProductoSKUOdoo):
                    self.db_operations.insertar_produc_ubicaciones(ProductoID, ProductoNombreOdoo, ProductoSKUOdoo)
                    self.db_operations.registro_logs(ProductoID, ProductoSKUOdoo, "INSERT", "Producto", None, ProductoSKUOdoo, None)
                    logging.warning("--- ProductoID %d INSERTADO CON SKU %s", ProductoID, ProductoSKUOdoo)
                    total_insertados += 1
                continue

            sku_mysql = existing_products[ProductoID]['ProductoSKUActual']
            nombre_mysql = existing_products[ProductoID]['ProductoNombre']
            stock_mysql_qra = existing_products[ProductoID]['StockQra']
            stock_mysql_cdmx = existing_products[ProductoID]['StockCDMX']

            if ProductoNombreOdoo and ProductoNombreOdoo != nombre_mysql:
                self.db_operations.actualizar_produc_nombre(ProductoNombreOdoo, ProductoID)
                self.db_operations.registro_logs(ProductoID, ProductoSKUOdoo, "UPDATE", "Nombre", nombre_mysql, ProductoNombreOdoo, None)
                logging.info("Nombre actualizado para ProductoID %d (SKU %s): '%s' -> '%s'", ProductoID, ProductoSKUOdoo, nombre_mysql, ProductoNombreOdoo)
                total_actualizados += 1
            if ProductoSKUOdoo and ProductoSKUOdoo != sku_mysql:
                self.db_operations.actualizar_produc_sku(ProductoSKUOdoo, ProductoID)
                self.db_operations.registro_logs(ProductoID, ProductoSKUOdoo, "UPDATE", "SKU", sku_mysql, ProductoSKUOdoo, None)
                logging.info("SKU actualizado para ProductoID %d: '%s' -> '%s'", ProductoID, sku_mysql, ProductoSKUOdoo)
                total_actualizados += 1

            for location_name, stock_dict in product_quantities.items():
                stock_mysql = stock_mysql_qra if location_name == 'QRA' else stock_mysql_cdmx
                stock_new = stock_dict.get(ProductoID, 0)
                stock_mysql = Decimal(stock_mysql).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if stock_mysql is not None else Decimal(0)
                stock_new = Decimal(stock_new).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if stock_new is not None else Decimal(0)
                if stock_mysql != stock_new:
                    self.db_operations.actualizar_produc_stock(location_name, stock_new, ProductoID)
                    self.db_operations.registro_logs(ProductoID, ProductoSKUOdoo, "UPDATE", "Stock", stock_mysql, stock_new, location_name)
                    logging.info("Stock actualizado para ProductoID %d (SKU %s) en %s: %s -> %s", ProductoID, sku_mysql, location_name, stock_mysql, stock_new)
                    total_actualizados += 1

        self.db.commit()
        logging.info("Total productos actualizados: %d", total_actualizados)
        logging.info("Total productos insertados: %d", total_insertados)

    def run(self):
        """Ejecuta la sincronización con mecanismo de bloqueo."""
        lock_file = open(LOCK_FILE_PATH, 'w')
        try:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            logging.info("Lock adquirido. Iniciando sincronización.")
            self.actualizar_productos()
        except IOError:
            logging.warning("Otra instancia del script está en ejecución. Saliendo.")
        finally:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            lock_file.close()
            logging.info("Lock liberado. Sincronización finalizada.")

if __name__ == "__main__":
    logger = configurar_logger(level=logging.DEBUG, log_to_file=True, log_file="sync_qro_log.log")
    processor = StockQroCM03()
    try:
        while True:
            processor.run()
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Ejecución interrumpida por el usuario.")
        processor.close_connections()
    except Exception as e:
        logging.error(f"Error inesperado: {e}")
        processor.close_connections()
