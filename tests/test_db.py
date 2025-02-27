# tests/test_db.py

import sys
import os

# Agregar `src` al path para permitir importar los módulos correctamente
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import pytest
from db.connection import DatabaseConnection

@pytest.fixture
def db_connection():
    """Crea una instancia de DatabaseConnection y la conecta."""
    db = DatabaseConnection()
    db.connect()
    yield db  # Proporciona la conexión para las pruebas
    db.disconnect()  # Se ejecuta al final de las pruebas

def test_db_connection_success(db_connection):
    """Prueba que la conexión a la base de datos se establezca correctamente."""
    assert db_connection.connection is not None, "Error: La conexión no se estableció"
    assert db_connection.connection.is_connected(), "Error: La conexión no está activa"

def test_db_disconnection(db_connection):
    """Prueba que la desconexión de la base de datos se realice correctamente."""
    db_connection.disconnect()
    assert not db_connection.connection.is_connected(), "Error: La conexión no se cerró correctamente"
