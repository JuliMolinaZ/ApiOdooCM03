# src/api/odoo_operations.py
# Operaciones para interactuar con Odoo

import sys
import logging
from api.odoo_client import OdooClient

class OdooOperations:
    def __init__(self, odoo_client):
        self.odoo = odoo_client
        
# Para albaranes_processor.py
    def obtener_tipo_operacion_interna(self):
        """Obtiene el ID del tipo de operación de transferencias internas desde Odoo."""
        try:
            logging.info("Obteniendo ID de tipo de operación interna...")
            picking_type_ids = self.odoo.execute_kw(
                'stock.picking.type', 'search', [[['code', '=', 'internal']]]
            )
            return picking_type_ids[0] if picking_type_ids else None
        except Exception as e:
            logging.error(f"Error al obtener el tipo de operación interna: {e}")
            return None
        
    def buscar_albaran_por_folio(self, folio):
        """Busca un albarán en Odoo por su folio y devuelve su ID."""
        domain = [('name', '=', folio)]
        albaranes = self.odoo.search('stock.picking', domain)
        return albaranes if albaranes else None

    def obtener_albaran_data(self, albaran_id):
        try:
            result = self.odoo.execute_kw(
                'stock.picking', 'read', [albaran_id],
                {'fields': ['id', 'partner_id', 'create_date', 'name', 'move_ids', 'priority', 'state']}
            )
            # Agregamos el log de depuración para revisar lo que se devuelve
            logging.debug(f"Resultado de la consulta a Odoo para el albarán {albaran_id}: {result}")

            if not result or not isinstance(result, list) or len(result) == 0:
                logging.error(f"Error: No se encontraron datos válidos para el albarán {albaran_id}.")
                return None

            albaran_data = result[0]
            if isinstance(albaran_data, dict):
                return albaran_data
            else:
                logging.error(f"Error: El albarán {albaran_id} no tiene la estructura de datos esperada.")
                return None
        except Exception as e:
            logging.error(f"Error obteniendo datos de albarán {albaran_id}: {e}")
            return None
    
    def buscar_albaranes_pendientes(self):
        domain = [("state", "=", "done"), ('name', 'like', 'WH/OUT/%')]  # Filtra albaranes listos para procesar
        albaranes = self.odoo.search("stock.picking", domain)
        return albaranes if albaranes else []
    
    def obtener_linea_data(self, linea_id):
        """Obtiene los datos de una línea de movimiento desde Odoo."""
        try:
            #logging.info(f"Obteniendo datos de la línea de movimiento con ID: {linea_id}")
            linea_data = self.odoo.execute_kw(
                'stock.move', 'read', [linea_id],
                {'fields': ['product_id', 'product_uom_qty', 'location_id', 'location_dest_id']}
            )[0]
            return linea_data
        except Exception as e:
            logging.error(f"Error al obtener los datos de la línea de movimiento: {e}")
            return None
        
# Para internal_transfer_processor.py
    def search_albaranes_cdex(self, priority=None, state=None, folio_like=None):
        """Busca albaranes con prioridad 1, estado 'done' y folio que comienza con 'WH/TCDMX y WH/RTCDMX'."""
        try:
            # Definir el dominio para la búsqueda
            domain = []

            if priority is not None:
                domain.append(['priority', '=', priority])
            if state is not None:
                domain.append(['state', '=', state])
            if folio_like:
                if isinstance(folio_like, list):  # Si es una lista, agregamos múltiples condiciones
                    domain.extend(['|'] * (len(folio_like) - 1))  # Agrega operadores OR
                    for folio in folio_like:
                        domain.append(['name', 'like', folio])
                else:
                    domain.append(['name', 'like', folio_like])

            # Realizar la búsqueda usando Odoo
            albaranes = self.odoo.search('stock.picking', domain)
            logging.info(f"Albaranes encontrados: {albaranes}")
            return albaranes
        except Exception as e:
            logging.error(f"Error al buscar albaranes: {e}")
            raise

# Para recibos_processor.py
    def obtener_recibos(self, fecha_actual):
        """Obtiene los recibos de Odoo con los filtros de fecha"""
        dominio = [
            ['picking_type_code', '=', 'incoming'],
            ['state', '=', 'done'],
            ['create_date', '>=', f'{fecha_actual} 00:00:00'],
            ['create_date', '<', f'{fecha_actual} 23:59:59']
        ]
        try:
            recibo_ids = self.odoo.execute_kw(
                'stock.picking', 'search', [dominio]
            )
            if not recibo_ids:
                logging.warning(f"No se encontraron recibos.")
                return []
            return recibo_ids
        except Exception as e:
            logging.error(f"Error al obtener recibos: {e}")
            return []
        
    def obtener_linea_data_recibos(self, linea_id):
        """Obtiene los datos de una línea de movimiento desde Odoo."""
        try:
            #logging.info(f"Obteniendo datos de la línea de movimiento con ID: {linea_id}")
            linea_data = self.odoo.execute_kw(
                'stock.move', 'read', [linea_id],
                {'fields': ['product_id', 'product_uom_qty']}
            )[0]
            return linea_data
        except Exception as e:
            logging.error(f"Error al obtener los datos de la línea de movimiento: {e}")
            return None
        
# Para stock_cedis_processor.py
    def obtener_sku_producto(self, sku):
        """Obtiene informacion del producto mediante el sku proporcionado"""
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
        except Exception as e:
            logging.error(f"Error al buscar el producto por SKU: {e}")

    def sububicaciones_producto(self, parent_location_id):
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
    
    def stock_quants(self, product_id, location_ids):
        try:
            return self.odoo.execute_kw('stock.quant', 'search_read',
                                        [[('product_id', '=', product_id),
                                          ('location_id', 'in', location_ids)]],
                                          {'fields': ['location_id', 'quantity']})
        except Exception as e:
            logging.error(f"Error al obtener el stock de Odoo: {e}")

# Para stock_qra_processor.py
    def sububicaciones_produc_total(self, location_id, offset=0, limit=0):
        try:
            logging.debug("Obteniendo productos en sububicaciones (Offset: %d, Limit: %d, LocationID: %d)", offset, limit, location_id)
            productos = self.odoo.execute_kw(
                'stock.quant', 'search_read',
                [[('location_id', 'child_of', location_id)]],
                {'fields': ['product_id', 'quantity', 'location_id'], 'offset': offset, 'limit': limit}
            )
            logging.debug("Productos obtenidos: %s", productos)
            return productos
        except Exception as e:
            logging.error("Error al obtener productos de Odoo: %s", e)
            return []
    
    def obtener_produc_total(self, product_ids):
        try:
            logging.debug("Obteniendo nombres de productos para IDs: %s", product_ids)
            product_data = self.odoo.execute_kw(
                'product.product', 'search_read',
                [[('id', 'in', product_ids)]],
                {'fields': ['id', 'name']}
            )
            logging.debug("Nombres obtenidos: %s", product_data)
            return {prod['id']: prod['name'] for prod in product_data}
        except Exception as e:
            logging.error("Error al obtener nombres de productos: %s", e)
            return {}
        
