# src/processor/internal_transfer_processor.py

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


class InternalTransferProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self.albaranes_especificos = ['']
        logging.info(f"InternalTransferProcessor inicializado con albaranes especificos: {self.albaranes_especificos}")

        # Inicializando las operaciones Odoo y BD
        self.odoo_operations = OdooOperations(self.odoo)
        self.db_operations = DatabaseOperations()
    
    def procesar_albaran(self, albaran_id):
        """Procesa un albarán específico, actualizando la base de datos y marcándolo como procesado."""

        try:
            logging.info(f"Procesando albaranID: {albaran_id}")

            # Lee detalles de albaran actual
            albaran_data = self.odoo_operations.obtener_albaran_data(albaran_id)
            if not albaran_data:
                logging.error(f"Error: No se obtuvieron datos validos para el albaran {albaran_id}")
                return

            albaran_folio = albaran_data['name']
            # Omitir albaranes que comiencen con 'CDMX/'
            if albaran_data['name'].startswith('CDMX/'):
                logging.info(f"Omitiendo albaran con folio {albaran_folio}")
                return
            # Solucion [ERROR] Error al procesar albaran 28531: 'bool' object is not subscriptable
            cliente = albaran_data['partner_id'][1] if albaran_data['partner_id'] else 'Cliente no definido'

            fecha_creacion = albaran_data['create_date']
            albaran_status = 'Pendiente'
            lineas = albaran_data['move_ids']

            logging.info(f"Detalles del albaran: Folio={albaran_folio}, Cliente={cliente}, Estado={albaran_status}")
        
            # Verifica si el albaran ya ha sido procesado
            if self.db_operations.verificar_albaran_procesado(albaran_id):
                logging.info(f"Albarán {albaran_id} ya ha sido procesado.")
                return

            # Insertar o actualizar la cabecera del albarán
            self.db_operations.insertar_o_actualizar_albaran(albaran_id, fecha_creacion, cliente, albaran_folio)

            # Procesar las líneas del albarán
            for linea_id in lineas:
                logging.info(f"Procesando línea ID: {linea_id}")
                linea_data = self.odoo_operations.obtener_linea_data(linea_id)
                if not linea_data:
                    logging.warning(f"Datos de linea no encontrado para la linea {linea_id}")
                    continue

                self.db_operations.insertar_detalle_albaran(linea_id, albaran_id, linea_data['product_id'][0], linea_data['product_uom_qty'], linea_data['location_dest_id'][1])

            self.db_operations.marcar_albaran_como_procesado(albaran_id)

            logging.info(f"Albaran {albaran_id} con folio {albaran_folio} procesado exitosamente")
        except Exception as e:
            print(f"Debug: Error capturado para albaran {albaran_id}: {repr(e)}")
            logging.error(f"Error al procesar albaran {albaran_id}: {e}")

    def procesar_albaranes_especificos(self):
        for albaran_folio in self.albaranes_especificos:
            logging.info(f"Buscando albarán con folio: {albaran_folio}")
            # Buscar el ID del albarán por su folio
            albaran_ids = self.odoo_operations.buscar_albaran_por_folio(albaran_folio)
            if albaran_ids:
                self.procesar_albaran(albaran_ids[0])
            else:
                logging.warning(f"Albarán con folio {albaran_folio} no encontrado.")

    def run(self):
        # Procesar albaranes específicos antes de iniciar el ciclo principal
        self.procesar_albaranes_especificos()
        logging.info("Iniciando ciclo principal para procesar albaranes.")

        # Ciclo principal para procesar albaranes según las condiciones especificadas
        while True:
            try:
                # Se busca albaranes con priority y con el folio de transferencia
                logging.info("Buscando albaranes con prioridad 1 y folio 'wh/tcdmx'.")
                albaranes_tcdmx = self.odoo_operations.search_albaranes_cdex(priority=1, folio_like=['WH/TCDMX%'])
                logging.info("Buscando albaranes con prioridad 1, status = listo y folio 'wh/int'.")
                albaranes_int = self.odoo_operations.search_albaranes_cdex(priority=1, folio_like=['WH/INT%'], state='assigned')

                albaranes = albaranes_tcdmx + albaranes_int

                # Procesar los albaranes desde el más reciente hacia atrás
                for albaran in albaranes[::-1]:
                    self.procesar_albaran(albaran)
                

            except Exception as e:
                logging.error(f"Error en la ejecución principal: {e}")

            logging.info("Esperando 60 segundos antes de la próxima búsqueda.")
            # Esperar 60 segundos antes de la próxima ejecución
            time.sleep(60)

if __name__ == "__main__":
    logger = configurar_logger(level=logging.INFO, log_to_file=False)
    processor = InternalTransferProcessor()
    try:
        processor.run()
    except KeyboardInterrupt:
        logging.info("Proceso interrumpido por el usuario.")
    finally:
        processor.close_connections()