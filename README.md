# Integración Odoo y Base de Datos - ApiOdooCM03

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Características](#características)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Requisitos Previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Ejecución de Pruebas](#ejecución-de-pruebas)
- [Ejecución de la Aplicación](#ejecución-de-la-aplicación)
- [Registro y Monitoreo](#registro-y-monitoreo)
- [Solución de Problemas](#solución-de-problemas)
- [Contribuciones](#contribuciones)
- [Licencia](#licencia)

## Descripción General

**ApiOdooCM03** es una aplicación desarrollada en Python para interactuar con el sistema Odoo y gestionar datos dentro de una base de datos MySQL. Este proyecto sincroniza productos entre Odoo y la base de datos MySQL, validando la existencia de productos, actualizando el stock en múltiples ubicaciones (QRO y CDMX), e insertando nuevos productos cuando es necesario, la aplicación también tiene pruebas unitarias para garantizar su funcionamiento correcto.

## Características

- **Integración con Odoo:** Recupera albaranes, productos, stocks, y sububicaciones desde Odoo.
- **Sincronización de Base de Datos:** Consulta, actualiza y/o inserta datos en MySQL.
- **Gestión de Stock:** Maneja el stock en distintas ubicaciones como QRO y CDMX.
- **Gestión de Albaranes:** Actualiza albaranes de acuerdo a folio.
- **Registro de Logs:** Monitorea la ejecución de procesos y registra posibles errores para solución de problemas.

## Estructura del proyecto

```
ApiOdooCM03/ 
├── README.md 
├── requirements.txt 
├── src/  
│   ├── api/ 
│   │   ├── __init__.py 
│   │   ├── odoo_operations.py 
│   │   └── odoo_client.py 
│   ├── config/ 
│   │   ├── __init__.py 
│   │   └── settings.py 
│   ├── db/ 
│   │   ├── __init__.py 
│   │   ├── connection.py 
│   │   └── operations.py 
│   ├── processors/ 
│   │   ├── __init__.py 
│   │   ├── albaranes_processor.py 
│   │   ├── base_processor.py 
│   │   ├── internal_transfer_processor.py 
│   │   ├── stock_cedis_processor.py 
│   │   ├── stock_qra_processor.py 
│   │   └── tarimas_processor.py 
│   └── utils/ 
│       ├── __init__.py 
│       └── logger.py 
└── tests/
    ├── __init__.py 
    └── test_db.py
```

## Requisitos Previos

- **Python 3.12** o superior
- **MySQL Server** accesible con credenciales adecuadas
- **Odoo** (versión compatible según el proyecto)
- **Git** para control de versiones
- **Herramientas de Entorno Virtual** (ejemplo: `venv`)

## Instalación

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu_usuario/ApiOdooCM03.git
cd ApiOdooCM03
```

### 2. Crear un Entorno Virtual

```bash
python3 -m venv venv

# Activar el entorno virtual
# En macOS/Linux:
source venv/bin/activate

# En Windows:
venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuración
### 1. Variables de Entorno
La aplicación utiliza variables de entorno para la configuración, gestionadas a través de un archivo .env. Este archivo debe ubicarse en el directorio raíz del proyecto.

```bash
touch .env
```

Dentro de este archivo, puedes agregar configuraciones como la URL de conexión a Odoo, credenciales de base de datos, etc.

## Ejecución de Pruebas

```bash
pytest -v tests
```

## Ejecución de la Aplicación
### 1. Navegar al Directorio Raíz del Proyecto

```bash
cd /ruta/al/proyecto/ApiOdooCM03/
```

### 2. Activar el Entorno Virtual

```bash
# En macOS/Linux:
source venv/bin/activate

# En Windows:
venv\Scripts\activate

#### 3. Ejecutar la Aplicación

python -m src.main
```

## Registro y Monitoreo
Los logs de la aplicación se encuentran en el archivo sync_log.log. Para monitorear en tiempo real:

```bash
tail -f sync_log.log
```

## Solución de Problemas

Si experimentas problemas, revisa los logs y asegúrate de que todas las dependencias estén correctamente instaladas. También verifica las configuraciones de las conexiones con la base de datos y Odoo.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o envía un pull request.

## Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.