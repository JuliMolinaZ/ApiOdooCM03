# src/processors/TarimasCM03.py
# Script dedicado a procesar albaranes que se encuentren en AlbaranStatus Supervisado y ProcesoConcatenacionRealizado en 0
# Se agrupan las validaciones por TarimaNumero y ValidacionSKU para cada AlbaranID y de validacionSKU obtiene el ProductoID.
# Se actualiza la columna TarimasConcatenadas en AlbaranDetalle con las tarimas correspondientes para cada ProductoID.
# Se marca el albarán como procesado (ProcesoConcatenacionRealizado = 1).

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

import time
import logging
from utils.logger import configurar_logger
from processors.base_processor import BaseProcessor
from api.odoo_operations import OdooOperations
from db.operations import DatabaseOperations

class TarimasProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()  
        self.odoo_operations = OdooOperations(self.odoo)
        self.db_operations = DatabaseOperations()

    def assign_tarimas(self):
        """Asigna tarimas a los Albaranes pendientes de procesamiento."""
        albaranes = self.db_operations.select_albaranes()
        if not albaranes:
                logging.warning("No hay albaranes supervisados sin procesar")
                return

        for albaran in albaranes:
            albaran_id = albaran['AlbaranID']
            logging.info(f"\nProcesando AlbaranID: {albaran_id}")

            validaciones = self.db_operations.select_validaciones(albaran_id)
            if not validaciones:
                    logging.warning(f"No hay validaciones para AlbaranID: {albaran_id}")
                    continue
        
            tarimas_por_producto = {}
            for validacion in validaciones:
                tarima_numero = validacion['TarimaNumero']
                sku_actual = validacion['ValidacionSKU']
                cantidad = validacion['CantidadValidaciones']

                #Obtener ProductoID a partir del SKU
                producto = self.db_operations.select_producto(sku_actual)

                if not producto:
                    logging.warning(f"Producto con SKU {sku_actual} no encontrado.")
                    continue
                    
                producto_id = producto['ProductoID']

                #Inicializar la lista si el ProductoID no existe aun
                if producto_id not in tarimas_por_producto:
                    tarimas_por_producto[producto_id] = []
                    
                #Añadir la tarima y cantidad a la lista correspondiente
                tarimas_por_producto[producto_id].append(f"{tarima_numero} ({cantidad})")

            #Actualizar AlabaranDetalle con las concatenaciones
            for producto_id, tarimas in tarimas_por_producto.items():
                concatenado = ", ".join(tarimas)

                #Actualizar la columna TarimasConcatenadas
                self.db_operations.update_albarandetalle(concatenado, albaran_id, producto_id)
                        
            #Marcar el Albaran como procesado sin cambiar el AlbaranStatus
            self.db_operations.update_albaranstatus(albaran_id)
            
            #Confirmar todos los cambios
            self.db.commit()
            logging.info(f"\nTodos los cambios han sido confirmados.")

            #Cerrar el cursor y la conexión
            self.db_operations.close()
            logging.info("Conexion a la base de datos cerrada.")

def main():
    try:
        logger = configurar_logger(level=logging.INFO, log_to_file=False)
        processor = TarimasProcessor()
        while True:
            logging.info("\n=== Iniciando proceso de asignación de tarimas ===")
            processor.assign_tarimas()
            logging.info("Esperando 15 segundos para la siguiente ejecución...\n")
            time.sleep(15) 
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario. Saliendo del script.")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
        main()
