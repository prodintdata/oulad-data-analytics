import pandas as pd
from sqlalchemy import create_engine
import os
import glob
from dotenv import load_dotenv

# Calculo las rutas subiendo un nivel para pararme en la raiz del proyecto OULAD
ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__)) # Python Files
ruta_raiz = os.path.dirname(ruta_subcarpeta)                # OULAD Raiz

# Cargo las variables de entorno apuntando de forma correcta a la raiz
ruta_env = os.path.join(ruta_raiz, ".env")
load_dotenv(dotenv_path=ruta_env)

# Defino la ruta hacia mi carpeta de datos puros en la raiz
ruta_carpeta_csv = os.path.join(ruta_raiz, "OULAD CSV")

def ejecutar_carga_pura():
    # Recoleccion segura de credenciales locales
    usuario = os.getenv("DB_USER")
    contrasena = os.getenv("DB_PASSWORD")
    servidor = os.getenv("DB_HOST")
    puerto = os.getenv("DB_PORT")
    base_datos = os.getenv("DB_NAME")
    
    engine = create_engine(f"mysql+pymysql://{usuario}:{contrasena}@{servidor}:{puerto}/{base_datos}")
    print(f"Conexion segura establecida con el esquema MySQL '{base_datos}'.")

    # 1. Bloque de archivos estandar mapeados con sus nombres reales en disco
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
        # Construyo la ruta absoluta hacia el archivo dentro de la carpeta OULAD CSV
        ruta_absoluta_csv = os.path.join(ruta_carpeta_csv, archivo)
        
        if os.path.exists(ruta_absoluta_csv):
            print(f"-> Procesando '{archivo}' desde OULAD CSV hacia la tabla '{tabla}'...")
            df = pd.read_csv(ruta_absoluta_csv)
            df.to_sql(tabla, con=engine, if_exists="append", index=False)
        else:
            print(f"Nota: No se encontro '{archivo}' en la carpeta OULAD CSV. Se asume ya cargado.")

    # 2. Bloque Dinamico para los archivos studentVle_*.csv particionados
    print("\n--- PASO 2: Detectando y Subiendo Archivos Particionados de studentVle ---")
    
    # Busco los archivos particionados directamente dentro de la carpeta OULAD CSV
    patron_busqueda = os.path.join(ruta_carpeta_csv, "studentVle_*.csv")
    archivos_vle = sorted(glob.glob(patron_busqueda))
    
    if not archivos_vle:
        print("No se encontraron archivos con el formato 'studentVle_*.csv' en la carpeta OULAD CSV.")
    else:
        print(f"Se detectaron {len(archivos_vle)} partes para studentVle.")
        
        for idx, archivo_particionado in enumerate(archivos_vle, start=1):
            nombre_corto = os.path.basename(archivo_particionado)
            print(f"-> [Parte {idx}/{len(archivos_vle)}] Insertando {nombre_corto}...")
            
            # Procesamiento eficiente por bloques de 250k filas para cuidar la RAM local
            for bloque in pd.read_csv(archivo_particionado, chunksize=250000):
                bloque.to_sql("studentVle", con=engine, if_exists="append", index=False)

    print("\n¡PROCESO COMPLETADO AL 100%! Toda la data pura esta unificada en MySQL.")

if __name__ == "__main__":
    ejecutar_carga_pura()