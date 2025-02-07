# src/processors/recibos_processor.py
# Script dedicado a insertar o actualizar recibos_especificos con folio por defecto (WH/IN/) desde ordenes de entrega en Odoo
# Observaciones hay recibos que no estan pero tienen priority y done pero no inserta, parece que no los tiene en cuenta.

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))


import time
import logging
import re
from datetime import datetime
from utils.logger import configurar_logger
from processors.base_processor import BaseProcessor
from api.odoo_operations import OdooOperations
from db.operations import DatabaseOperations

class RecibosCM03Processor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self.recibos_especificos = ['WH/IN/00382']
        logging.info("Inicializando RecibosCM03Processor")

        # Inicializando las operaciones Odoo y BD
        self.odoo_operations = OdooOperations(self.odoo)
        self.db_operations = DatabaseOperations()

    def obtener_recibos(self):
        """Obtener recepciones de Odoo con picking_type_code 'incoming', estado 'done' y fecha de creación actual"""
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        return self.odoo_operations.obtener_recibos(fecha_actual)

    def validar_origen(self, origen):
        """Valida si el origen del recibo cumple con el formato esperado"""
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

            # Verifica si el albaran ya ha sido procesado
            if self.db_operations.verificar_recibo_procesado(recibo_id):
                return

            # Verifica su el recibo existe o no en la base de datos
            #procesado = self.db_operations.verificar_recibo_procesado(recibo_id)
            #logging.info(f"Resultado de la consulta para ReciboID {recibo_id}: {procesado}")            

            recibo_folio = recibo_data['name']
            partner_name = recibo_data['partner_id'][1]
            logging.info(f"Procesando recibo ID: {recibo_id}, Folio: {recibo_folio}, Proveedor: {partner_name}")
            if not self.validar_origen(recibo_data.get('origin')):
                logging.warning(f"Recibo {recibo_data['name']} omitido. Origen no válido.")
                return

            # Inserta el recibo
            fecha_creacion = recibo_data['create_date']
            lineas = recibo_data['move_ids']
            self.db_operations.insertar_o_actualizar_recibo(recibo_id, fecha_creacion, partner_name, recibo_data)

            # Insertar líneas del recibo
            for linea_id in lineas:
                linea_data = self.odoo_operations.obtener_linea_data(linea_id)
                product_id = linea_data['product_id'][0]
                cantidad = linea_data['product_uom_qty']

                # Limpieza de datos del producto antes de insertarlos (si es necesario)
                productos_limpios = self.limpiar_datos_productos(str(product_id))

                # Inserción del detalle del recibo
                self.db_operations.insertar_detalle_recibo(linea_id, recibo_id, product_id, cantidad)

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


if __name__ == "__main__":
    logger = configurar_logger(level=logging.INFO, log_to_file=False)
    processor = RecibosCM03Processor()
    try:
        processor.run()
    except KeyboardInterrupt:
        processor.close_connections()
        logging.info("Ejecución interrumpida por el usuario.")
    except Exception as e:
        logging.error(f"Error inesperado: {e}")
        processor.close_connections()
