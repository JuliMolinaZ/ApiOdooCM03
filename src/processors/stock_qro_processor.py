# src/processors/stock_qra_processor.py
# Actualiza todos los productos existentes en la BD, considerando el stock de QRA y CDMX usando un diccionario de ubicaciones

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

import time
import msvcrt
import logging
from utils.logger import configurar_logger
from processors.base_processor import BaseProcessor
from api.odoo_operations import OdooOperations
from db.operations import DatabaseOperations

LOCK_FILE_PATH = 'sync_script.lock'
UBICACIONES = {
    'QRA': 8,  # ID de la ubicación WH/Stock QRA
    'CDMX': 38  # ID de la ubicación WH/Stock CDMX
}

# Configuración del log
logging.basicConfig(
    level=logging.DEBUG,  # Cambiado a DEBUG para mayor detalle
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("sync_log.log")
    ], force=True
)

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
        """Sincroniza los productos entre Odoo y MySQL, considerando el stock de varias ubicaciones."""
        existing_products = self.obtener_productos_existentes()
        if not existing_products:
            logging.warning("No se encontraron productos en MySQL")
            return

        offset = 0
        limit = 100
        product_quantities = {location: {} for location in UBICACIONES}

        # Obtener stock de todas las ubicaciones definidas en el diccionario
        for location_name, location_id in UBICACIONES.items():
            logging.info("Obteniendo productos para la ubicación: %s (ID: %d)", location_name, location_id)
            while True:
                products = self.obtener_productos_en_sububicaciones(location_id, offset, limit)
                if not products:
                    break

                for product in products:
                    ProductoID = product['product_id'][0]
                    product_quantities[location_name][ProductoID] = product_quantities[location_name].get(ProductoID, 0) + product['quantity']
                    logging.debug("%s ProductoID %d: Cantidad acumulada = %s", location_name, ProductoID, product_quantities[location_name][ProductoID])

                offset += limit

            offset = 0  # Resetear el offset para la siguiente ubicación

        # Unir todos los IDs de productos obtenidos
        all_product_ids = set().union(*[quantities.keys() for quantities in product_quantities.values()])
        product_names = self.obtener_nombres_productos(list(all_product_ids))
        total_actualizados = 0

        for ProductoID in all_product_ids:
            if ProductoID not in existing_products:
                logging.warning("ProductoID %d no encontrado en MySQL. Saltando actualización.", ProductoID)
                continue

            ProductoNombreOdoo = product_names.get(ProductoID, existing_products[ProductoID]['ProductoNombre'])
            ProductoSKU = existing_products[ProductoID]['ProductoSKUActual']
            nombre_mysql = existing_products[ProductoID]['ProductoNombre']
            stock_mysql_qra = existing_products[ProductoID]['StockQra']
            stock_mysql_cdmx = existing_products[ProductoID]['StockCDMX']

            # Actualizar nombre si es necesario
            if ProductoNombreOdoo != nombre_mysql:
                self.db_operations.actualizar_produc_nombre(ProductoNombreOdoo, ProductoID)
                logging.info("Nombre actualizado para ProductoID %d (SKU %s): '%s' -> '%s'", ProductoID, ProductoSKU, nombre_mysql, ProductoNombreOdoo)
                total_actualizados += 1

            # Actualizar stock de cada ubicación si es necesario
            for location_name, stock_dict in product_quantities.items():
                stock_mysql = stock_mysql_qra if location_name == 'QRA' else stock_mysql_cdmx
                stock_new = stock_dict.get(ProductoID, 0)

                if stock_mysql != stock_new:
                    self.db_operations.actualizar_produc_stock(location_name, stock_new, ProductoID)
                    logging.info("Stock actualizado para ProductoID %d (SKU %s) en %s: %s -> %s", ProductoID, ProductoSKU, location_name, stock_mysql, stock_new)
                    total_actualizados += 1

        self.db.commit()
        logging.info("Total productos actualizados: %d", total_actualizados)

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

