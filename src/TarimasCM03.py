# src/TarimasCM03.py
# Script dedicado a procesar albaranes que se encuentren en AlbaranStatus Supervisado y ProcesoConcatenacionRealizado en 0
# Se agrupan las validaciones por TarimaNumero y ValidacionSKU para cada AlbaranID y de validacionSKU obtiene el ProductoID.
# Se actualiza la columna TarimasConcatenadas en AlbaranDetalle con las tarimas correspondientes para cada ProductoID.
# Se marca el albarán como procesado (ProcesoConcatenacionRealizado = 1).

from base_processor import BaseProcessor
import logging
import time

class TarimasProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()  

    def assign_tarimas(self):
        with self.db.connection.cursor(dictionary=True) as cursor:
            select_albaranes_query = """ SELECT AlbaranID FROM Albaran WHERE AlbaranStatus = 'Supervisado' AND ProcesoConcatenacionRealizado = 0 LIMIT 1000 """
            cursor.execute(select_albaranes_query)
            albaranes = cursor.fetchall()
            if not albaranes:
                logging.warning("No hay albaranes supervisados sin procesar.")
                return

            for albaran in albaranes:
                albaran_id = albaran['AlbaranID']
                logging.info(f"\nProcesando AlbaranID: {albaran_id}")

                #Obtener validaciones agrupadas por TarimaNumero y ProductoID
                select_validaciones_query = """SELECT ta.TarimaNumero, vt.ValidacionSKU, COUNT(*) AS CantidadValidaciones
                               FROM ValidacionT vt 
                               JOIN TarimasA ta ON vt.TarimaID = ta.TarimaID 
                               WHERE vt.AlbaranID = %s 
                               GROUP BY ta.TarimaNumero, vt.ValidacionSKU"""
                cursor.execute(select_validaciones_query, (albaran_id, ))
                validaciones = cursor.fetchall()

                # Ahora 'validaciones_dict' es una lista de diccionarios
                logging.debug(f"Tipo de validaciones: {type(validaciones)}")
                logging.debug(f"Primer elemento de validaciones: {validaciones[0]}")


                if not validaciones:
                    print(f"No hay validaciones para AlbaranID: {albaran_id}")     

                #Crear diccionario para almacenar las concatenaciones por ProductoID
                tarimas_por_producto = {}
                for validacion in validaciones:
                    tarima_numero = validacion['TarimaNumero']
                    sku = validacion['ValidacionSKU']
                    cantidad = validacion['CantidadValidaciones']

                    #Obtener ProductoID a partir del SKU
                    select_producto_query = """ SELECT ProductoID FROM Productos WHERE ProductoSKUActual = %s LIMIT 1 """
                    cursor.execute(select_producto_query, (sku, ))
                    producto = cursor.fetchone()

                    if not producto:
                        logging.warning(f"Producto con SKU {sku} no encontrado.")
                        continue
                    
                    #producto_id = producto['ProductoID']
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
                    update_albarandetalle_query = """UPDATE AlbaranDetalle SET TarimasConcatenadas = %s WHERE AlbaranID = %s AND ProductoID = %s"""
                    cursor.execute(update_albarandetalle_query, (concatenado, albaran_id, producto_id))
                    logging.info(f"Actualizado AlbaranDetalle para ProductoID: {producto_id} con Tarimas: {concatenado}")

                #Marcar el Albaran como procesado sin cambiar el AlbaranStatus
                update_albarandetalle_query = """UPDATE Albaran SET ProcesoConcatenacionRealizado = 1 WHERE AlbaranID = %s"""
                cursor.execute(update_albarandetalle_query, (albaran_id, ))
                logging.info(f"AlbaranID {albaran_id} marcado como procesado.")
            
            #Confirmar todos los cambios
            self.db.connection.commit()
            logging.info(f"\nTodos los cambios han sido confirmados.")

            #Cerrar el cursor y la conexión
            cursor.close()
            self.db.connection.close()
            logging.info("Conexion a la base de datos cerrada.")

def main():
    try:
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
