# src/utils/logger.py
import logging
import sys
import os

def configurar_logger(level=logging.INFO, log_to_file=False, log_file="app_log.log"):
    """
    Configura el logger de la aplicación.
    :param level: El nivel de logging, por defecto INFO.
    :param log_to_file: Si se debe loguear a un archivo.
    :param log_file: Nombre del archivo de log, por defecto 'app_log.log'.
    :return: Logger configurado.
    """
    # Ruta predeterminada para los logs
    log_directory = os.path.join(os.path.dirname(__file__), '..', 'logs')

    # Asegurarse de que la carpeta de logs exista
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    
    # Si log_to_file es True, construir la ruta completa al archivo de log
    log_file_path = os.path.join(log_directory, log_file) if log_to_file else None

    # Configurar el logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Crear el manejador de consola
    stream_handler = logging.StreamHandler(sys.stdout)

    # Si se necesita loguear en un archivo
    if log_file_path:
        file_handler = logging.FileHandler(log_file_path)
        logger.addHandler(file_handler)

    # Agregar el manejador de consola
    logger.addHandler(stream_handler)

    # Configurar el formato
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    stream_handler.setFormatter(formatter)
    
    if log_file_path:
        file_handler.setFormatter(formatter)
    
    return logger
