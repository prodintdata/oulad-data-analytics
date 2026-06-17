import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Configuración de ruta absoluta para variables de entorno locales
ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.dirname(ruta_subcarpeta)
ruta_env = os.path.join(ruta_raiz, ".env")
load_dotenv(dotenv_path=ruta_env)

def generar_datos_ordinales():
    # 1. Conexión segura a la base de datos
    usuario = os.getenv("DB_USER")
    contrasena = os.getenv("DB_PASSWORD")
    servidor = os.getenv("DB_HOST")
    puerto = os.getenv("DB_PORT")
    base_datos = os.getenv("DB_NAME")
    
    engine = create_engine(f"mysql+pymysql://{usuario}:{contrasena}@{servidor}:{puerto}/{base_datos}")
    print("Conexión exitosa para procesamiento analítico de variables.")

    # 2. Extraer el perfil de los estudiantes
    print("Leyendo tabla 'studentInfo' desde MySQL...")
    df_students = pd.read_sql("SELECT * FROM studentInfo", con=engine)

    # 3. Mapeo de Diccionarios Ordinales Homologados con la Base de Datos
    mapeo_educacion = {
        'No Formal quals': 0,
        'Lower Than A Level': 1,
        'A Level or Equivalent': 2,
        'HE Qualification': 3,
        'Post Graduate Qualification': 4
    }

    mapeo_edad = {
        '0-35': 0,
        '35-55': 1,
        '55<=': 2  # Corregido para que coincida con el texto exacto del diagnóstico
    }

    # Se incluye 'Unknown' mapeado como 0 y se desplazan los porcentajes de 1 a 10
    mapeo_imd = {
        'Unknown': 0,
        '0-10%': 1, '10-20%': 2, '20-30%': 3, '30-40%': 4, '40-50%': 5,
        '50-60%': 6, '60-70%': 7, '70-80%': 8, '80-90%': 9, '90-100%': 10
    }

    # Variable Objetivo (Esencial para Machine Learning)
    mapeo_resultado = {
        'Withdrawn': 0,
        'Fail': 1,
        'Pass': 2,
        'Distinction': 3
    }

    # Codificación de variables binarias para optimización analítica
    mapeo_genero = {'M': 0, 'F': 1}
    mapeo_discapacidad = {'N': 0, 'Y': 1}

    print("Aplicando ingeniería de características (Transformación Ordinal)...")
    
    # Aplicación segura de mapeos creando las nuevas columnas analíticas
    df_students['education_ordinal'] = df_students['highest_education'].map(mapeo_educacion)
    df_students['age_band_ordinal'] = df_students['age_band'].map(mapeo_edad)
    
    # Limpieza preventiva de espacios en blanco e imd_band
    df_students['imd_band_clean'] = df_students['imd_band'].str.strip()
    df_students['imd_band_ordinal'] = df_students['imd_band_clean'].map(mapeo_imd)
    
    # Mapeo de nuevas variables integradas
    df_students['final_result_ordinal'] = df_students['final_result'].map(mapeo_resultado)
    df_students['gender_encoded'] = df_students['gender'].map(mapeo_genero)
    df_students['disability_encoded'] = df_students['disability'].map(mapeo_discapacidad)
    
    # Remoción de columna auxiliar
    df_students.drop(columns=['imd_band_clean'], inplace=True)

    # 4. Asegurar la destrucción manual preventiva en MySQL usando transacciones limpias
    nueva_tabla = "student_analytics"
    with engine.begin() as con:
        con.execute(text(f"DROP TABLE IF EXISTS {nueva_tabla};"))

    # 5. Inyectar la nueva estructura procesada a MySQL
    print(f"Escribiendo registros transformados en la nueva tabla '{nueva_tabla}'...")
    df_students.to_sql(nueva_tabla, con=engine, if_exists="replace", index=False)
    
    print(f"¡Éxito total! Tabla '{nueva_tabla}' creada con todas las columnas ordinales listas.")

if __name__ == "__main__":
    generar_datos_ordinales()