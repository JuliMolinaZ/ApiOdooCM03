# src/processors/stock_cedis_processor.py
# Script dedicado a insertar o actualizar producto especificado por medio de su SKU en la tabla Productos

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

import logging
from utils.logger import configurar_logger
from processors.base_processor import BaseProcessor
from api.odoo_operations import OdooOperations
from db.operations import DatabaseOperations

# SKU a probar
sku_a_probar = [' ', ' ', ' ']

# Diccionario de ubicaciones
UBICACIONES = {
    'QRA': 8,
    'CDMX': 38
}

class StockCedisProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self.odoo_operations = OdooOperations(self.odoo)
        self.db_operations = DatabaseOperations()

    def obtener_producto_por_sku(self, sku):
        return self.odoo_operations.obtener_sku_producto(sku)

    def obtener_sububicaciones(self, parent_location_id):
        return self.odoo_operations.sububicaciones_producto(parent_location_id)

    def obtener_stock_por_sububicacion(self, product_id, location_ids):
        try:
            stock_quants = self.odoo_operations.stock_quants(product_id, location_ids)
            stock_detallado = {}

            for quant in stock_quants:
                loc_id = quant['location_id'][0]
                quantity = quant['quantity']
                if loc_id in stock_detallado:
                    stock_detallado[loc_id] += quantity
                else:
                    stock_detallado[loc_id] = quantity

            logging.info(f"Stock por sububicación: {stock_detallado}")
            return stock_detallado
        
        except Exception as e:
            logging.error(f"Error al obtener stock por sububicación: {e}")
            sys.exit(1)

    def registrar_stock_en_bd(self, producto_id, producto_nombre, sku_actual, stock_total, stock_qra, stock_cdmx):
        if self.db_operations.sku_en_bd(sku_actual):
            self.db_operations.actualizar_producto(producto_id, producto_nombre, stock_total, stock_qra, stock_cdmx, sku_actual)
        else:
            if producto_id is not None and isinstance(producto_id, int):
                self.db_operations.insertar_producto(producto_id, producto_nombre, sku_actual, stock_total, stock_qra, stock_cdmx)
            else:
                logging.warning(f"No se insertó el producto con SKU={sku_actual} porque ProductoID es inválido o None")
        self.db.commit()
        
    def run(self):
        try:
            for sku in sku_a_probar:
                producto = self.obtener_producto_por_sku(sku_a_probar)
                product_id = producto.get('id')

                # Obtener sububicaciones de QRA
                location_ids_qra = self.obtener_sububicaciones(UBICACIONES['QRA'])
                stock_qra_detallado = self.obtener_stock_por_sububicacion(product_id, location_ids_qra)
                stock_qra = stock_qra_detallado.get(UBICACIONES['QRA'], 0)

                # Obtener sububicaciones de CDMX
                stock_cdmx_location_ids = self.obtener_sububicaciones(UBICACIONES['CDMX'])
                stock_cdmx_detallado = self.obtener_stock_por_sububicacion(product_id, stock_cdmx_location_ids)
                stock_cdmx = sum(stock_cdmx_detallado.values())

                # Stock total
                stock_total = stock_qra + stock_cdmx
                self.registrar_stock_en_bd(
                    producto_id=product_id,
                    producto_nombre=producto['name'],
                    sku_actual=sku_a_probar,
                    stock_total=stock_total,
                    stock_qra=stock_qra,
                    stock_cdmx=stock_cdmx
                )
            logging.info("Proceso completado con éxito.")
        except Exception as e:
            logging.error(f"Error durante el procesamiento: {e}")

if __name__ == "__main__":
    logger = configurar_logger(level=logging.INFO, log_to_file=False)
    processor = StockCedisProcessor()
    processor.run()
    processor.close_connections()
