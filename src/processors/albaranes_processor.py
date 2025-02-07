# src/processors/albaranes_processor.py
# Script dedicado a insertar o actualizar albaranes con folio por defecto (WH/OUT/) desde ordenes de entrega en Odoo
# En albaranes_especificos, se declaran folios fuera de los por defecto que se deseen insertar en la tabla Albaran (ej. (WH/TCDMX/)

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

import time
import logging
from datetime import datetime
from utils.logger import configurar_logger
from processors.base_processor import BaseProcessor
from api.odoo_operations import OdooOperations
from db.operations import DatabaseOperations

class AlbaranesCM03Processor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self.odoo_operations = OdooOperations(self.odoo)
        self.db_operations = DatabaseOperations()
        self.albaranes_especificos = ['WH/TCDMX/00001']
        self.picking_type_internal_id = self.odoo_operations.obtener_tipo_operacion_interna()
        logging.info("Inicializado AlbaranesCM03Processor")

    def procesar_albaran(self, albaran_id):
        """Procesa un albarán específico, actualizando la base de datos y marcándolo como procesado."""
        try:
            start_time = time.time()  # Marcar el tiempo al inicio del procesamiento

            logging.info(f"Procesando albarán ID: {albaran_id}")

            # Lee detalles de albaran actual
            albaran_data = self.odoo_operations.obtener_albaran_data(albaran_id)
            if not albaran_data:
                logging.warning(f"Albaran {albaran_id} no encontrado.")
                return

            albaran_folio = albaran_data['name']
            if albaran_data['name'].startswith('CDMX/'):
                logging.info(f"Albarán {albaran_folio} omitido.")
                return

            cliente = albaran_data['partner_id'][1]
            fecha_creacion = albaran_data['create_date']
            lineas = albaran_data['move_ids']

            if self.db_operations.verificar_albaran_procesado(albaran_id):
                logging.info(f"Albarán {albaran_id} ya ha sido procesado.")
                return

            self.db_operations.insertar_o_actualizar_albaran(albaran_id, fecha_creacion, cliente, albaran_folio)
            
            for linea_id in lineas:
                linea_data = self.odoo_operations.obtener_linea_data(linea_id)
                if not linea_data:
                    continue

                self.db_operations.insertar_detalle_albaran(linea_id, albaran_id, linea_data['product_id'][0], linea_data['product_uom_qty'], linea_data['location_dest_id'][1])

            self.db_operations.marcar_albaran_como_procesado(albaran_id)
            
            end_time = time.time()
            processing_time = end_time - start_time
            logging.info(f"Albarán {albaran_id} con folio {albaran_folio} procesado exitosamente en {processing_time:.2f} segundos.")

        except Exception as e:
            logging.error(f"Error procesando albarán {albaran_id}: {e}")

    def procesar_albaranes_especificos(self):
        """Procesa los albaranes específicos predefinidos."""
        for albaran_folio in self.albaranes_especificos:
            albaran_ids = self.odoo_operations.buscar_albaran_por_folio(albaran_folio)
            if albaran_ids:
                self.procesar_albaran(albaran_ids[0])
            else:
                logging.warning(f"Albarán con folio {albaran_folio} no encontrado.")

    def run(self):
        """Ciclo principal para procesar todos los albaranes pendientes."""
        self.procesar_albaranes_especificos()

        while True:
            try:
                logging.info("Buscando albaranes pendientes...")
                albaranes_pendientes = self.odoo_operations.buscar_albaranes_pendientes()
                if albaranes_pendientes:
                    for albaran_id in albaranes_pendientes:
                        if not self.db_operations.verificar_albaran_procesado(albaran_id):
                            self.procesar_albaran(albaran_id)
                else:
                    logging.info("No hay albaranes pendientes por procesar.")

            except Exception as e:
                logging.error(f"Error en ciclo principal: {e}")
            
            time.sleep(60)

if __name__ == "__main__":
    logger = configurar_logger(level=logging.INFO, log_to_file=False)
    processor = AlbaranesCM03Processor()
    try:
        processor.run()
    except KeyboardInterrupt:
        processor.close_connections()
        logging.info("Ejecución interrumpida por el usuario.")
