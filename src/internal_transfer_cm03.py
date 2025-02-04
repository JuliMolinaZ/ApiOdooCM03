# src/internal_transfer.py

import time  # Asegúrate de importar time
from base_processor import BaseProcessor
from datetime import datetime
import logging

class InternalTransferProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self.albaranes_especificos = ['WH/TCDMX/00001', 'WH/OUT/16012', 'WH/OUT/16010']
        logging.info(f"InternalTransferProcessor inicializado con albaranes específicos: {self.albaranes_especificos}")

    def procesar_albaran(self, albaran_id):
        try:
            logging.info(f"Procesando albarán ID: {albaran_id}")
            # Leer los detalles del albarán actual
            albaran_data = self.odoo.execute_kw(
                'stock.picking', 'read', [albaran_id],
                {'fields': ['id', 'partner_id', 'create_date', 'name', 'move_ids', 'priority', 'state']}
            )

            if not albaran_data:
                logging.warning(f"No se encontraron datos para el albarán ID: {albaran_id}")
                return

            albaran_data = albaran_data[0]
            albaran_folio = albaran_data['name']

            # Omitir albaranes que comiencen con 'CDMX/'
            if albaran_folio.startswith('CDMX/'):
                logging.info(f"Omitiendo albarán con folio {albaran_folio}.")
                return

            cliente = albaran_data['partner_id'][1]
            fecha_creacion = albaran_data['create_date']
            albaran_prioridad = albaran_data['priority']
            albaran_status = 'Pendiente'
            lineas = albaran_data['move_ids']

            logging.info(f"Detalles del albarán: Folio={albaran_folio}, Cliente={cliente}, Estado={albaran_status}")

            # Verificar si el albarán ya ha sido procesado
            query = "SELECT Procesado FROM Albaran WHERE AlbaranID = %s"
            result = self.db.execute_query(query, (albaran_id,))

            if result:
                procesado = result[0][0]
                if procesado == 1:
                    logging.info(f"El albarán ID: {albaran_id} ya ha sido procesado. Saltando procesamiento.")
                    return

            # Obtener la fecha y hora actual
            fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Insertar o actualizar la cabecera del albarán
            self.db.execute_proc('InsertOrUpdateAlbaranTest', (
                albaran_id,
                fecha_creacion,
                cliente,
                albaran_folio,
                fecha_actual,  # AlbaranPrioridad
                albaran_status,
                None,  # UsuarioAsignado
                None,  # AlbaranComentarios
                0.0,
                '2024-01-01',
                None   # UsuarioSupervisor
            ))
            logging.info(f"Cabecera del albarán ID: {albaran_id} insertada/actualizada.")

            # Procesar las líneas del albarán
            for linea_id in lineas:
                logging.info(f"Procesando línea ID: {linea_id}")
                linea_data = self.odoo.execute_kw(
                    'stock.move', 'read', [linea_id],
                    {'fields': ['product_id', 'product_uom_qty', 'location_id', 'location_dest_id']}
                )

                if linea_data:
                    linea_data = linea_data[0]
                    producto_id = linea_data['product_id'][0]
                    producto_nombre = linea_data['product_id'][1]
                    cantidad = linea_data['product_uom_qty']
                    ubicacion_id = linea_data['location_id'][1]
                    ubicacion_dest_id = linea_data['location_dest_id'][1]

                    logging.info(f"Línea procesada: Producto={producto_nombre}, Cantidad={cantidad}, Ubicación={ubicacion_id}, Destino={ubicacion_dest_id}")

                    self.db.execute_proc('InsertOrUpdateAlbaranDetalle', (
                        linea_id,
                        albaran_id,
                        producto_id,
                        cantidad,
                        0.0,  # Cantidad surtida
                        ubicacion_id,
                        ubicacion_dest_id,
                        None,  # ProductoSupervisado
                        None   # Tarima
                    ))
                    logging.info(f"Línea ID: {linea_id} insertada/actualizada.")

            # Marcar el albarán como procesado
            update_query = "UPDATE Albaran SET Procesado = 1 WHERE AlbaranID = %s"
            self.db.execute_query(update_query, (albaran_id,))
            self.db.commit()
            logging.info(f"Albarán ID: {albaran_id} marcado como procesado.")

        except Exception as e:
            logging.error(f"Error al procesar albarán ID {albaran_id}: {e}")

    def procesar_albaranes_especificos(self):
        for albaran_folio in self.albaranes_especificos:
            try:
                logging.info(f"Buscando albarán con folio: {albaran_folio}")
                # Buscar el ID del albarán por su folio
                albaran_ids = self.odoo.execute_kw(
                    'stock.picking', 'search', [[['name', '=', albaran_folio]]]
                )
                
                if albaran_ids:
                    logging.info(f"Albarán encontrado con folio {albaran_folio}: ID={albaran_ids[0]}")
                    self.procesar_albaran(albaran_ids[0])
                else:
                    logging.warning(f"Albarán con folio {albaran_folio} no encontrado.")

            except Exception as e:
                logging.error(f"Error al buscar albarán con folio {albaran_folio}: {e}")

    def run(self):
        # Procesar albaranes específicos antes de iniciar el ciclo principal
        self.procesar_albaranes_especificos()
        logging.info("Iniciando ciclo principal para procesar albaranes.")

        # Ciclo principal para procesar albaranes según las condiciones especificadas
        while True:
            try:
                logging.info("Buscando albaranes con prioridad 1, estado 'assigned' y folio que comienza con 'CDMX/'.")
                albaranes = self.odoo.execute_kw(
                    'stock.picking', 'search', [
                        [['priority', '=', '1'], ['state', '=', 'assigned'], ['name', 'like', 'CDMX/%']]
                    ]
                )
                logging.info(f"Albaranes encontrados: {albaranes}")

                # Procesar los albaranes desde el más reciente hacia atrás
                for albaran in albaranes[::-1]:
                    self.procesar_albaran(albaran)

            except Exception as e:
                logging.error(f"Error en la ejecución principal: {e}")

            logging.info("Esperando 60 segundos antes de la próxima búsqueda.")
            # Esperar 60 segundos antes de la próxima ejecución
            time.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler() 
        ]
    )
    processor = InternalTransferProcessor()
    try:
        processor.run()
    except KeyboardInterrupt:
        logging.info("Proceso interrumpido por el usuario.")
    finally:
        processor.close_connections()