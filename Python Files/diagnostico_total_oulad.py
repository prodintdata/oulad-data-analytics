import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# Configuro la ruta absoluta para asegurar la lectura correcta del archivo .env
ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.dirname(ruta_subcarpeta)
ruta_env = os.path.join(ruta_raiz, ".env")
load_dotenv(dotenv_path=ruta_env)

def ejecutar_auditoria_total():
    # Cargo mis credenciales del archivo local protegido
    usuario = os.getenv("DB_USER")
    contrasena = os.getenv("DB_PASSWORD")
    servidor = os.getenv("DB_HOST")
    puerto = os.getenv("DB_PORT")
    base_datos = os.getenv("DB_NAME")
    
    # Establezco conexion con el motor de MySQL
    engine = create_engine(f"mysql+pymysql://{usuario}:{contrasena}@{servidor}:{puerto}/{base_datos}")
    print("=== AUDITORIA INTEGRAL DE CALIDAD DE DATOS: ESQUEMA OULAD ===\n")

    # Lista oficial con las 7 tablas del ecosistema para barrerlas en paralelo
    tablas_sistema = [
        "courses", 
        "assessments", 
        "vle", 
        "studentInfo", 
        "studentRegistration", 
        "studentAssessment", 
        "studentVle"
    ]

    # BLOQUE 1: Escaneo automatico de registros, nulos y tipos de datos por tabla
    print("--- FASE 1: Perfilado de Estructuras y Diagnostico de Vacios ---")
    for tabla in tablas_sistema:
        print(f"\nAnalizando tabla: {tabla}")
        
        # Optimizacion: Si es la tabla masiva de clicks, solo leo las primeras filas para mapear sus tipos
        # de datos y uso un conteo rapido para no saturar la memoria RAM de mi equipo
        if tabla == "studentVle":
            total_filas = pd.read_sql("SELECT COUNT(*) as total FROM studentVle", con=engine).iloc[0]['total']
            df_muestra = pd.read_sql("SELECT * FROM studentVle LIMIT 1000", con=engine)
            
            # Para el calculo de nulos en la masiva, dejo que MySQL lo procese directo en el motor
            query_nulos_vle = """
                SELECT 
                    SUM(CASE WHEN code_module IS NULL THEN 1 ELSE 0 END) as code_module_nulls,
                    SUM(CASE WHEN code_presentation IS NULL THEN 1 ELSE 0 END) as code_presentation_nulls,
                    SUM(CASE WHEN id_student IS NULL THEN 1 ELSE 0 END) as id_student_nulls,
                    SUM(CASE WHEN id_site IS NULL THEN 1 ELSE 0 END) as id_site_nulls,
                    SUM(CASE WHEN date IS NULL THEN 1 ELSE 0 END) as date_nulls,
                    SUM(CASE WHEN sum_click IS NULL THEN 1 ELSE 0 END) as sum_click_nulls
                FROM studentVle
            """
            df_nulos_vle = pd.read_sql(query_nulos_vle, con=engine)
            
            print(f"Total de registros en disco: {total_filas}")
            print("Tipos de datos detectados:")
            print(df_muestra.dtypes)
            print("Valores nulos por columna calculados en el motor:")
            print(df_nulos_vle.iloc[0])
        else:
            # Para las demas tablas estandar, hago la extraccion directa a memoria
            df_local = pd.read_sql(f"SELECT * FROM {tabla}", con=engine)
            total_filas = len(df_local)
            conteo_nulos = df_local.isnull().sum()
            
            print(f"Total de registros en disco: {total_filas}")
            print("Tipos de datos detectados:")
            print(df_local.dtypes)
            print("Valores nulos encontrados por columna:")
            print(conteo_nulos[conteo_nulos > 0] if conteo_nulos.sum() > 0 else "Tabla limpia, no contiene valores nulos")
            
        print("-" * 60)

    # BLOQUE 2: Pruebas cruzadas de Integridad Referencial (Buscando Huerfanos para FK)
    print("\n--- FASE 2: Diagnostico Relacional contra Fallas de Llaves Foraneas ---")
    
    # Prueba A: Alumnos huerfanos en la tabla de calificaciones
    q_huerfanos_sa = """
        SELECT COUNT(DISTINCT sa.id_student) as huerfanos
        FROM studentAssessment sa
        LEFT JOIN studentInfo si ON sa.id_student = si.id_student
        WHERE si.id_student IS NULL;
    """
    huerfanos_sa = pd.read_sql(q_huerfanos_sa, con=engine).iloc[0]['huerfanos']
    print(f"Estudiantes en studentAssessment que no existen en el maestro studentInfo: {huerfanos_sa}")

    # Prueba B: Evaluaciones huerfanas en la tabla de calificaciones
    q_huerfanos_sa_assess = """
        SELECT COUNT(*) as huerfanos
        FROM studentAssessment sa
        LEFT JOIN assessments a ON sa.id_assessment = a.id_assessment
        WHERE a.id_assessment IS NULL;
    """
    huerfanos_sa_assess = pd.read_sql(q_huerfanos_sa_assess, con=engine).iloc[0]['huerfanos']
    print(f"Calificaciones que apuntan a codigos de evaluacion inexistentes en assessments: {huerfanos_sa_assess}")

    # Prueba C: Alumnos huerfanos en el registro de matriculas
    q_huerfanos_sr = """
        SELECT COUNT(*) as huerfanos
        FROM studentRegistration sr
        LEFT JOIN studentInfo si 
            ON sr.code_module = si.code_module 
            AND sr.code_presentation = si.code_presentation 
            AND sr.id_student = si.id_student
        WHERE si.id_student IS NULL;
    """
    huerfanos_sr = pd.read_sql(q_huerfanos_sr, con=engine).iloc[0]['huerfanos']
    print(f"Matriculas registradas que no hacen match con ningun perfil de studentInfo: {huerfanos_sr}")

    # Prueba D: Clicks huerfanos dirigidos a recursos del catalogo virtual
    q_huerfanos_sv_vle = """
        SELECT COUNT(*) as huerfanos
        FROM studentVle sv
        LEFT JOIN vle v ON sv.id_site = v.id_site
        WHERE v.id_site IS NULL;
    """
    huerfanos_sv_vle = pd.read_sql(q_huerfanos_sv_vle, con=engine).iloc[0]['huerfanos']
    print(f"Clicks en studentVle asociados a recursos id_site excluidos de la tabla vle: {huerfanos_sv_vle}")

    # Prueba E: Clicks huerfanos ejecutados por alumnos sin perfil maestro
    q_huerfanos_sv_student = """
        SELECT COUNT(*) as huerfanos
        FROM studentVle sv
        LEFT JOIN studentInfo si 
            ON sv.code_module = si.code_module 
            AND sv.code_presentation = si.code_presentation 
            AND sv.id_student = si.id_student
        WHERE si.id_student IS NULL;
    """
    print("Evaluando relacion de la bitacora de clicks masiva contra el maestro de alumnos...")
    huerfanos_sv_student = pd.read_sql(q_huerfanos_sv_student, con=engine).iloc[0]['huerfanos']
    print(f"Clicks en studentVle ejecutados por estudiantes no registrados en studentInfo: {huerfanos_sv_student}")

    print("\n=== AUDITORIA INTEGRAL FINALIZADA CON EXITO ===")

if __name__ == "__main__":
    ejecutar_auditoria_total()