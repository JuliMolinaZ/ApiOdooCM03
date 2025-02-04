# src/test_database.py

from database import Database

def test_database_connection():
    db = Database()
    db.connect()
    if db.connection:
        print("Conexión establecida correctamente.")
    else:
        print("Fallo en la conexión.")
    db.disconnect()

if __name__ == "__main__":
    test_database_connection()