import pandas as pd
from sqlalchemy import create_engine
import os
import glob
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

def ejecutar_carga_pura():
    # ----------------------------------------------------------------------
    # RECOLECCIÓN SEGURA DE CREDENCIALES (Desde el archivo .env)
    # ----------------------------------------------------------------------
    usuario = os.getenv("DB_USER")
    contrasena = os.getenv("DB_PASSWORD")
    servidor = os.getenv("DB_HOST")
    puerto = os.getenv("DB_PORT")
    base_datos = os.getenv("DB_NAME")
    
    # Motor de conexión SQLAlchemy sin contraseñas escritas en el código
    engine = create_engine(f"mysql+pymysql://{usuario}:{contrasena}@{servidor}:{puerto}/{base_datos}")
    print(f"Conexión segura establecida con el esquema MySQL '{base_datos}'.")

    # 1. Bloque de archivos estándar 
    archivos_estandar = [
        ("courses.csv", "courses"),
        ("assessments.csv", "assessments"),
        ("vle.csv", "vle"),
        ("studentInfo.csv", "studentInfo"),
        ("studentRegistration.csv", "studentRegistration"),
        ("studentAssessment.csv", "studentAssessment")
    ]

    print("\n--- PASO 1: Subiendo Tablas Base y Perfiles ---")
    for archivo, tabla in archivos_estandar:
        if os.path.exists(archivo):
            print(f"-> Procesando '{archivo}' hacia la tabla '{tabla}'...")
            df = pd.read_csv(archivo)
            df.to_sql(tabla, con=engine, if_exists="append", index=False)
        else:
            print(f"Nota: Si '{archivo}' ya fue cargado, puedes ignorar este aviso.")

    # 2. Bloque Dinámico para los archivos studentVle_*.csv
    print("\n--- PASO 2: Detectando y Subiendo Archivos Particionados de studentVle ---")
    
    # Buscamos en la carpeta cualquier archivo que coincida con el patrón de la captura
    archivos_vle = sorted(glob.glob("studentVle_*.csv"))
    
    if not archivos_vle:
        print("No se encontraron archivos con el formato 'studentVle_*.csv'. Verificalo.")
    else:
        print(f"Se detectaron {len(archivos_vle)} partes para studentVle: {archivos_vle}")
        
        for idx, archivo_particionado in enumerate(archivos_vle, start=1):
            print(f"-> [Parte {idx}/{len(archivos_vle)}] Insertando {archivo_particionado}...")
            # Procesamiento eficiente por bloques de 250k filas para cuidar la RAM
            for bloque in pd.read_csv(archivo_particionado, chunksize=250000):
                bloque.to_sql("studentVle", con=engine, if_exists="append", index=False)

    print("\n¡PROCESO COMPLETADO AL 100%! Toda LA data pura está unificada en MySQL.")

if __name__ == "__main__":
    ejecutar_carga_pura()