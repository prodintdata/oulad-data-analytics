import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Configuración de ruta absoluta para variables de entorno locales
ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.dirname(ruta_subcarpeta)
ruta_env = os.path.join(ruta_raiz, ".env")
load_dotenv(dotenv_path=ruta_env)

def ejecutar_etl_investigacion():
    # 1. CONEXIÓN A LA BASE DE DATOS
    usuario = os.getenv("DB_USER")
    contrasena = os.getenv("DB_PASSWORD")
    servidor = os.getenv("DB_HOST")
    puerto = os.getenv("DB_PORT")
    base_datos = os.getenv("DB_NAME")
    
    engine = create_engine(f"mysql+pymysql://{usuario}:{contrasena}@{servidor}:{puerto}/{base_datos}")
    print("Conexión exitosa.")

    # 2. EXTRACCIÓN (E) - Fuentes exclusivas y unificadas
    print("Extrayendo variables demográficas y ordinales...")
    df_demografia = pd.read_sql("SELECT * FROM student_analytics", con=engine)
    
    print("Extrayendo histórico de evaluaciones...")
    df_assess = pd.read_sql("SELECT * FROM v_full_domain_assess", con=engine)
    
    print("Extrayendo interacciones VLE (Bitácora masiva)...")
    df_vle = pd.read_sql("SELECT * FROM v_full_domain_vle", con=engine)

    # 3. TRANSFORMACIÓN (T)
    print("Calculando los indicadores de rendimiento académico y puntualidad...")
    # Variable booleana: 1 si entregó antes o en la fecha límite, 0 si se retrasó
    df_assess['a_tiempo'] = (df_assess['date_submitted'] <= df_assess['date_planned']).astype(int)
    
    # Agrupación por estudiante para resumir el bloque de evaluaciones
    df_assess_grouped = df_assess.groupby('id_student').agg(
        nota_promedio=('score', 'mean'),
        nota_maxima=('score', 'max'),
        nota_minima=('score', 'min'),
        total_evaluaciones_entregadas=('id_assessment', 'count'),
        porcentaje_entregas_a_tiempo=('a_tiempo', 'mean')
    ).reset_index()
    
    # Convertimos la proporción de entregas a tiempo a formato porcentual (0-100%)
    df_assess_grouped['porcentaje_entregas_a_tiempo'] = (df_assess_grouped['porcentaje_entregas_a_tiempo'] * 100).round(2)

    print("Contando y organizando los clics de cada alumno en el aula virtual...")
    # Volumen absoluto de actividad digital por alumno
    df_vle_total = df_vle.groupby('id_student').agg(total_clicks_plataforma=('sum_click', 'sum')).reset_index()
    
    # Pivote dinámico completo: genera una columna para cada tipo de recurso sin exclusión previa
    df_vle_pivot = df_vle.pivot_table(
        index='id_student', 
        columns='activity_type', 
        values='sum_click', 
        aggfunc='sum', 
        fill_value=0
    ).reset_index()
    
    # Estandarización de nombres: agregamos el prefijo 'clicks_' para identificar las variables
    nuevos_nombres = {col: f"clicks_{col}" for col in df_vle_pivot.columns if col != 'id_student'}
    df_vle_pivot.rename(columns=nuevos_nombres, inplace=True)

    # Consolidación del bloque de comportamiento digital
    df_vle_final = pd.merge(df_vle_total, df_vle_pivot, on='id_student', how='inner')

    print("Consolidando el Dataset ")
    # Ensamble general mediante LEFT JOIN asegurando mantener la totalidad del universo demográfico
    df_master = pd.merge(df_demografia, df_assess_grouped, on='id_student', how='left')
    df_master = pd.merge(df_master, df_vle_final, on='id_student', how='left')

    # TRATAMIENTO SEGURO DE NULOS:
    # Seleccionamos dinámicamente solo las columnas numéricas que se generaron en los cruces
    import numpy as np # Para evitar fallos en la funcion seltect_dtypes
    columnas_numericas = df_master.select_dtypes(include=[np.number]).columns
    # Excluimos id_student para mantener el ID intacto
    columnas_a_rellenar = [col for col in columnas_numericas if col != 'id_student']
    
    print("Corrigiendo valores ausentes (Inyectando ceros en registros sin actividad)...")
    # Aplicamos el reemplazo columna por columna de forma secuencial y segura
    for col in columnas_a_rellenar:
        df_master[col] = df_master[col].fillna(0)
    
    # Ajustes finales de redondeo para consistencia métrica
    df_master['nota_promedio'] = df_master['nota_promedio'].round(2)
    # ======================================================================

    # 4. CARGA (L) - Inyección en MySQL (LO QUE SIGUE ABAJO SE QUEDA IGUAL)
    tabla_destino = "tablon_investigacion_oulad"

    with engine.begin() as con:
        con.execute(text(f"DROP TABLE IF EXISTS {tabla_destino};"))
        
    print(f"Escribiendo los datos en la tabla '{tabla_destino}'...")
    df_master.to_sql(tabla_destino, con=engine, if_exists="replace", index=False)
    
    print(f"\n¡El tablón '{tabla_destino}' fue creado exitosamente.")
    print(f"Estructura final: {df_master.shape[0]} estudiantes (filas) y {df_master.shape[1]} variables (columnas) listas para análisis.")

if __name__ == "__main__":
    ejecutar_etl_investigacion()