# src/StockCedisCM03.py
# Script dedicado a insertar o actualizar producto especifido por medio de su SKU en la tabla Productos, solo actualiza StockQra

from base_processor import BaseProcessor
import logging
import sys

# SKU a probar
sku_a_probar = "CM01PRBAGMPPREMNA"

# Diccionario de ubicaciones
UBICACIONES = {
    'QRA': 8,
    'CDMX': 38
}

class StockCedisProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()

    def obtener_producto_por_sku(self, sku):
        try:
            productos = self.odoo.execute_kw('product.product', 'search_read',
                                            [[('default_code', '=', sku)]],
                                            {'fields': ['id', 'name', 'qty_available']})
            if productos:
                producto = productos[0]
                logging.info(f"Datos del producto recibido de Odoo: {producto}")
                return producto
            else:
                logging.error(f"No se encontró ningún producto con el SKU '{sku}'.")
                sys.exit(1)
        except Exception as e:
            logging.error(f"Error al buscar el producto por SKU: {e}")
            sys.exit(1)

    def obtener_sububicaciones(self, parent_location_id):
        try:
            sub_locations = self.odoo.execute_kw('stock.location', 'search_read',
                                                [[('parent_path', 'like', '/%s/%%' % parent_location_id)]],
                                                {'fields': ['id', 'name', 'parent_path']})
            location_ids = [loc['id'] for loc in sub_locations]
            # Incluir la ubicación principal
            location_ids.append(parent_location_id)
            logging.info(f"Sububicaciones encontradas (Total {len(location_ids)}): {location_ids}")
            return location_ids
        except Exception as e:
            logging.error(f"Error al obtener sububicaciones: {e}")
            sys.exit(1)

    def obtener_stock_por_sububicacion(self, product_id, location_ids):
        try:
            stock_quants = self.odoo.execute_kw('stock.quant', 'search_read',
                                                       [[('product_id', '=', product_id),
                                                         ('location_id', 'in', location_ids)]],
                                                       {'fields': ['location_id', 'quantity']})
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
        try:
            with self.db.connection.cursor() as cursor:
                query_select = "SELECT ProductoID FROM Productos WHERE ProductoSKUActual = %s"
                cursor.execute(query_select, (sku_actual,))
                result = cursor.fetchone()

                if result:
                    # Actualizar el producto existente
                    query_update = """
                        UPDATE Productos
                        SET ProductoNombre = %s, ProductoStock = %s, StockQra = %s, StockCDMX = %s
                        WHERE ProductoSKUActual = %s
                    """
                    cursor.execute(query_update, (producto_nombre, stock_total, stock_qra, stock_cdmx, sku_actual))
                    logging.info(f"Producto actualizado en la BD: SKU={sku_actual}, StockTotal={stock_total}, StockQro={stock_qra}, StockCDMX={stock_cdmx}")
                else:
                    # Insertar un nuevo producto
                    logging.info(f"Intentando insertar ProductoID={producto_id}, ProductoNombre={producto_nombre}, SKU={sku_actual}")
                    if producto_id is not None and isinstance(producto_id, int):
                        query_insert = """
                            INSERT INTO Productos (ProductoID, ProductoNombre, ProductoSKUActual, ProductoStock, StockQra, StockCDMX)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(query_insert, (producto_id, producto_nombre, sku_actual, stock_total, stock_qra, stock_cdmx))
                        logging.info(f"Producto insertado en la BD: ProductoID={producto_id}, SKU={sku_actual}, StockTotal={stock_total}, StockQro={stock_qra}, StockCDMX={stock_cdmx}")
                    else:
                        logging.warning(f"No se insertó el producto con SKU={sku_actual} porque ProductoID es inválido o None")

                self.db.connection.commit()
        except Exception as e:
            logging.error(f"Error al registrar en la base de datos: {e}")
        finally:
            if self.db.connection:
                self.db.connection.close()

    def run(self):
        producto = self.obtener_producto_por_sku(sku_a_probar)
        product_id = producto.get('id')

        # Obtener sububicaciones de QRA
        location_ids_qra = self.obtener_sububicaciones(UBICACIONES['QRA'])
        stock_qra_detallado = self.obtener_stock_por_sububicacion(product_id, location_ids_qra)
        stock_qra = stock_qra_detallado.get(UBICACIONES['QRA'], 0)

        #Obtener sububicaciones de CDMX
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

if __name__ == "__main__":
    processor = StockCedisProcessor()
    processor.run()
    processor.close_connections()
