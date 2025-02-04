# src/AlbaranesCM03.py
# Script dedicado a insertar o actualizar albaranes con folio por defecto (WH/OUT/) desde ordenes de entrega en Odoo
# En albaranes_especificos, se declaran folios fuera de los por defecto que se deseen insertar en la tabla Albaran (ej. (WH/TCDMX/)

import time
from base_processor import BaseProcessor
from datetime import datetime
import logging

class AlbaranesCM03Processor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self.albaranes_especificos = ['WH/TCDMX/00001']
        self.picking_type_internal_id = self.obtener_tipo_operacion_interna()
        logging.info("Inicializado AlbaranesCM03Processor")

    def obtener_tipo_operacion_interna(self):
        """ Obtiene el ID del tipo de operación de transferencias internas desde Odoo."""
        try:
            logging.info("Obteniendo ID de tipo de operación interna...")
            picking_type_ids = self.odoo.execute_kw(
                'stock.picking.type', 'search', [[['code', '=', 'internal']]]
            )
            return picking_type_ids[0] if picking_type_ids else None
        except Exception as e:
            logging.error(f"Error al obtener el tipo de operación interna: {e}")
            return None

    def procesar_albaran(self, albaran_id):
        """Procesa un albarán específico, actualizando la base de datos y marcándolo como procesado."""
        try:
            start_time = time.time()  # Marcar el tiempo al inicio del procesamiento

            logging.info(f"Procesando albarán ID: {albaran_id}")
            albaran_data = self.odoo.execute_kw(
                'stock.picking', 'read', [albaran_id],
                {'fields': ['id', 'partner_id', 'create_date', 'name', 'move_ids', 'priority', 'state']},
            )[0]

            albaran_folio = albaran_data['name']
            if albaran_data['name'].startswith('CDMX/'):
                logging.info(f"Albarán {albaran_folio} omitido.")
                return

            cliente = albaran_data['partner_id'][1]
            fecha_creacion = albaran_data['create_date']
            lineas = albaran_data['move_ids']

            # Verificar si el albarán ya ha sido procesado
            if self.db.execute_query("SELECT Procesado FROM Albaran WHERE AlbaranID = %s", (albaran_id,)):
                logging.info(f"Albarán {albaran_id} ya ha sido procesado.")
                return

            # Llamar al procedimiento almacenado para actualizar el albarán
            self.db.execute_proc('InsertOrUpdateAlbaranTest', (
                albaran_id, fecha_creacion, cliente, albaran_data['name'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Pendiente', None, None, 0.0, '2024-01-01', None
            ))
            
            for linea_id in lineas:
                linea_data = self.odoo.execute_kw(
                    'stock.move', 'read', [linea_id],
                    {'fields': ['product_id', 'product_uom_qty', 'location_id', 'location_dest_id']},
                )[0]

                product_id = linea_data['product_id'][0]
                product_name = linea_data['product_id'][1]
                quantity = linea_data['product_uom_qty']
                location = linea_data['location_id'][1]
                location_dest = linea_data['location_dest_id'][1]
                logging.info(f"     Insertando producto: SKU={product_id}, Nombre={product_name}, Cantidad={quantity}, Ubicacion={location}, Destino={location_dest}")


                self.db.execute_proc('InsertOrUpdateAlbaranDetalle', (
                    linea_id, 
                    albaran_id, 
                    linea_data['product_id'][0],
                    linea_data['product_uom_qty'], 
                    0.0,
                    None, 
                    linea_data['location_dest_id'][1], 
                    None, 
                    None
                ))

            # Marcar albarán como procesado
            self.db.execute_query("UPDATE Albaran SET Procesado = 1 WHERE AlbaranID = %s", (albaran_id,))
            self.db.commit()
            
            end_time = time.time()  # Marcar el tiempo al finalizar el procesamiento
            processing_time = end_time - start_time  # Calcular el tiempo transcurrido
            logging.info(f"Albarán {albaran_id} con folio {albaran_folio} procesado exitosamente en {processing_time:.2f} segundos.")

        except Exception as e:
            logging.error(f"Error procesando albarán {albaran_id}: {e}")

    def procesar_albaranes_especificos(self):
        """Procesa los albaranes específicos predefinidos."""
        for albaran_folio in self.albaranes_especificos:
            albaran_ids = self.odoo.execute_kw(
                'stock.picking', 'search', [[['name', '=', albaran_folio]]]
            )
            if albaran_ids:
                self.procesar_albaran(albaran_ids[0])
            else:
                logging.warning(f"Albarán con folio {albaran_folio} no encontrado.")

    def run(self):
        """Ciclo principal para procesar todos los albaranes pendientes."""
        # Procesar los albaranes específicos
        self.procesar_albaranes_especificos()

        # Procesar todos los albaranes pendientes
        while True:
            try:
                logging.info("Buscando albaranes pendientes...")
                albaranes_pendientes = self.odoo.execute_kw(
                    'stock.picking', 'search', [
                        [['state', '=', 'assigned'], ['name', 'like', 'WH/OUT%']]
                    ]
                )
                
                for albaran_id in albaranes_pendientes:
                    # Verificar si el albarán ya ha sido procesado antes de procesarlo
                    if not self.db.execute_query("SELECT Procesado FROM Albaran WHERE AlbaranID = %s", (albaran_id,)):
                        self.procesar_albaran(albaran_id)

            except Exception as e:
                logging.error(f"Error en ciclo principal: {e}")
            
            time.sleep(60)  # Esperar 60 segundos antes de la próxima iteración

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )
    processor = AlbaranesCM03Processor()
    try:
        processor.run()
    except KeyboardInterrupt:
        processor.close_connections()
        logging.info("Ejecución interrumpida por el usuario.")
