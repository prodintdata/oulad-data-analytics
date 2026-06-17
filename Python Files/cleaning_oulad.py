import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Configuro la ruta absoluta para el archivo .env local
ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.dirname(ruta_subcarpeta)
ruta_env = os.path.join(ruta_raiz, ".env")
load_dotenv(dotenv_path=ruta_env)

def pipeline_only_cleaning():
    # Extraigo las credenciales seguras
    usuario = os.getenv("DB_USER")
    contrasena = os.getenv("DB_PASSWORD")
    servidor = os.getenv("DB_HOST")
    puerto = os.getenv("DB_PORT")
    base_datos = os.getenv("DB_NAME")
    
    engine = create_engine(f"mysql+pymysql://{usuario}:{contrasena}@{servidor}:{puerto}/{base_datos}")
    print("=== INICIANDO PIPELINE DE CLEANING EXCLUSIVO EN PYTHON ===\n")

    # REGLA 1: Tabla courses
    # Como documente en el Excel, aplico un strip preventivo para remover micro-espacios
    # en las columnas de texto que serviran como llaves primarias
    print("[1/6] Purificando tabla courses...")
    df_courses = pd.read_sql("SELECT * FROM courses", con=engine)
    df_courses['code_module'] = df_courses['code_module'].str.strip()
    df_courses['code_presentation'] = df_courses['code_presentation'].str.strip()
    df_courses.to_sql("courses", con=engine, if_exists="replace", index=False)

    # REGLA 2: Tabla assessments (Imputacion Dinamica por Mapeo)
    # Segun definimos en la matriz, hago un merge con la longitud real de la tabla courses
    # para no colocar un valor fijo y evitar sesgos cronologicos en el EDA. Luego muevo a INT
    print("[2/6] Purificando tabla assessments con imputacion dinamica por mapeo...")
    df_assessments = pd.read_sql("SELECT * FROM assessments", con=engine)
    df_courses_aux = pd.read_sql("SELECT code_module, code_presentation, module_presentation_length FROM courses", con=engine)
    
    df_assessments['code_module'] = df_assessments['code_module'].str.strip()
    df_assessments['code_presentation'] = df_assessments['code_presentation'].str.strip()
    df_courses_aux['code_module'] = df_courses_aux['code_module'].str.strip()
    df_courses_aux['code_presentation'] = df_courses_aux['code_presentation'].str.strip()

    df_merged = pd.merge(df_assessments, df_courses_aux, on=['code_module', 'code_presentation'], how='left')
    df_assessments['date'] = df_assessments['date'].fillna(df_merged['module_presentation_length']).astype(int)
    df_assessments['weight'] = df_assessments['weight'].astype(int)
    df_assessments.to_sql("assessments", con=engine, if_exists="replace", index=False)

    # REGLA 3: Tabla vle
    # Aplico la regla del Excel: imputo las semanas faltantes con 0 indicando disponibilidad
    # transversal desde el dia uno, evitando incongruencias con la bitacora de clicks
    print("[3/6] Purificando tabla vle e imputando recursos transversales con cero...")
    df_vle = pd.read_sql("SELECT * FROM vle", con=engine)
    df_vle['code_module'] = df_vle['code_module'].str.strip()
    df_vle['code_presentation'] = df_vle['code_presentation'].str.strip()
    df_vle['week_from'] = df_vle['week_from'].fillna(0).astype(int)
    df_vle['week_to'] = df_vle['week_to'].fillna(0).astype(int)
    df_vle.to_sql("vle", con=engine, if_exists="replace", index=False)

    # REGLA 4: Tabla studentInfo
    print("[4/6] Purificando tabla studentInfo y preservando registros de privacidad...")
    df_info = pd.read_sql("SELECT * FROM studentInfo", con=engine)
    df_info['code_module'] = df_info['code_module'].str.strip()
    df_info['code_presentation'] = df_info['code_presentation'].str.strip()
    df_info['imd_band'] = df_info['imd_band'].fillna("Unknown").str.strip()
    
    # Fuerzo el borrado manual directo en MySQL usando una transaccion limpia
    with engine.begin() as con:
        con.execute(text("DROP TABLE IF EXISTS studentInfo;"))
    df_info.to_sql("studentInfo", con=engine, if_exists="replace", index=False)


    # REGLA 5: Tabla studentRegistration
    print("[5/6] Purificando tabla studentRegistration y normalizando variables de desercion...")
    df_reg = pd.read_sql("SELECT * FROM studentRegistration", con=engine)
    df_reg['code_module'] = df_reg['code_module'].str.strip()
    df_reg['code_presentation'] = df_reg['code_presentation'].str.strip()
    df_reg['date_registration'] = df_reg['date_registration'].fillna(0).astype('int64')
    df_reg['date_unregistration'] = df_reg['date_unregistration'].astype('Int64')
    
    # Fuerzo el borrado manual preventivo
    with engine.begin() as con:
        con.execute(text("DROP TABLE IF EXISTS studentRegistration;"))
    df_reg.to_sql("studentRegistration", con=engine, if_exists="replace", index=False)


    # REGLA 6: Tabla studentAssessment
    print("[6/6] Purificando tabla studentAssessment con penalizacion por omision...")
    df_sa = pd.read_sql("SELECT * FROM studentAssessment", con=engine)
    df_sa['score'] = df_sa['score'].fillna(0).astype(int)
    
    # Fuerzo el borrado manual preventivo
    with engine.begin() as con:
        con.execute(text("DROP TABLE IF EXISTS studentAssessment;"))
    df_sa.to_sql("studentAssessment", con=engine, if_exists="replace", index=False)

    print("\n=== PIPELINE DE CLEANING COMPLETADO EN MYSQL DISCO ===")

if __name__ == "__main__":
    pipeline_only_cleaning()