# src/RecibosCM03.py
# Script dedicado a insertar o actualizar recibos_especificos con folio por defecto (WH/IN/) desde ordenes de entrega en Odoo
# Observaciones hay recibos que no estan pero tienen priority y done pero no inserta, parece que no los tiene en cuenta.

import time
from base_processor import BaseProcessor
from datetime import datetime
import logging
import re

class RecibosCM03Processor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self.recibos_especificos = ['WH/IN/00382']
        logging.info("Inicializando RecibosCM03Processor")

    def obtener_recibos(self):
        """Obtener recepciones de Odoo con picking_type_code 'incoming', estado 'done' y fecha de creación actual"""
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        dominio = [
            ['picking_type_code', '=', 'incoming'],
            ['state', '=', 'done'],
            ['create_date', '>=', f'{fecha_actual} 00:00:00'],
            ['create_date', '<', f'{fecha_actual} 23:59:59']
        ]
        #logging.info(f"Dominio para obtener recibos: {dominio}")    
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

    def validar_origen(self, origen):
        #"""Valida si el origen del recibo cumple con el formato esperado"""
        #return isinstance(origen, str) and origen.startswith("P") and len(origen) == 6
        """Validar si el origen del recibo cumple con el formato esperado"""
        return re.match(r'P\d{5}$', origen)

    def limpiar_datos_productos(self, productos):
        """Limpia los datos de los productos extrayendo números"""
        pattern = re.compile(r'\d+')
        numeros = pattern.findall(productos)
        return list(set(map(int, numeros)))

    def procesar_recibo_principal(self):
        """Procesar los recibos obtenidos individualmente."""
        recibos = self.obtener_recibos()
        if recibos is None:
            return # Si no se encontraron recibos, terminamos el proceso
        for recibo_id in recibos:
            self.procesar_recibo(recibo_id)

    def procesar_recibo(self, recibo_id):
        """Procesa un recibo individual"""
        try:
            # Obtiene datos del recibo
            recibo_data = self.odoo.execute_kw(
                'stock.picking', 'read', [recibo_id], 
                {'fields': ['id', 'partner_id', 'create_date', 'name', 'move_ids', 'priority', 'state', 'origin']}
            )[0]

            # Verifica su el recibo existe o no en la base de datos
            procesado = self.db.execute_query("SELECT COUNT(*) FROM Recibos WHERE ReciboID = %s", (recibo_id,))
            if procesado[0]['COUNT(*)'] > 0:
                logging.info(f"El recibo ID: {recibo_id} ya existe en la base de datos. Saltando procesamiento.")
                return
            

            recibo_folio = recibo_data['name']
            partner_name = recibo_data['partner_id'][1]
            logging.info(f"Procesando recibo ID: {recibo_id}, Folio: {recibo_folio}, Proveedor: {partner_name}")
            if not self.validar_origen(recibo_data.get('origin')):
                logging.warning(f"Recibo {recibo_data['name']} omitido. Origen no válido.")
                return

            # Inserta el recibo
            fecha_creacion = recibo_data['create_date']
            lineas = recibo_data['move_ids']
            self.db.execute_proc('InsertOrUpdateRecibo', (
                recibo_id, fecha_creacion, partner_name, recibo_data['name'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                'Pendiente', None, None, 0.0, '2024-01-01', None
            ))

            # Insertar líneas del recibo
            for linea_id in lineas:
                linea_data = self.odoo.execute_kw(
                    'stock.move', 'read', [linea_id], {'fields': ['product_id', 'product_uom_qty']}
                )[0]
                product_id = linea_data['product_id'][0]
                cantidad = linea_data['product_uom_qty']

                # Limpieza de datos del producto antes de insertarlos (si es necesario)
                productos_limpios = self.limpiar_datos_productos(str(product_id))

                # Inserción del detalle del recibo
                self.db.execute_proc('InsertOrUpdateReciboDetalle', (
                    linea_id, recibo_id, product_id, cantidad, None
                ))

            self.db.commit()
            logging.info(f"Recibo {recibo_id}, Folio: {recibo_folio}, Proveedor: {partner_name} procesado exitosamente.")
        except Exception as e:
            logging.error(f"Error procesando recibo {recibo_id}: {str(e)}")

    def procesar_recibos_especificos(self):
        """Procesar recibos específicos antes de iniciar el ciclo principal"""
        for recibo_folio in self.recibos_especificos:
            try:
                recibo_ids = self.odoo.execute_kw(
                    'stock.picking', 'search', [[['name', '=', recibo_folio]]]
                )
                if recibo_ids:
                    self.procesar_recibo(recibo_ids[0])
                else:
                    logging.warning(f"Recibo con folio {recibo_folio} no encontrado.")
            except Exception as e:
                logging.error(f"Error al procesar recibo específico {recibo_folio}: {e}")

    def run(self):
        """Función principal del script"""
        self.procesar_recibos_especificos()
        while True:
            try:
                recibos = self.obtener_recibos()
                if not recibos:
                    logging.warning("No hay recibos disponibles para procesar.")
                    time.sleep(10)
                    continue
                for recibo_id in recibos:
                    self.procesar_recibo(recibo_id)
                time.sleep(10)  # Espera 10 segundos antes de la siguiente iteración
            except Exception as e:
                logging.error(f"Error en ciclo principal: {e}")
                time.sleep(30)  # Espera más tiempo en caso de error

    def close_connections(self):
        """Cierra conexiones de base de datos y Odoo"""
        if hasattr(self.db, 'close'):
            self.db.close()  # Cerramos la conexión si tiene el método 'close'
        else:
            logging.warning("No se pudo cerrar la conexión, 'close' no está disponible.")
        logging.info("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler()]
    )
    processor = RecibosCM03Processor()
    try:
        processor.run()
    except KeyboardInterrupt:
        processor.close_connections()
        logging.info("Ejecución interrumpida por el usuario.")
    except Exception as e:
        logging.error(f"Error inesperado: {e}")
        processor.close_connections()
