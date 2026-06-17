import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from scipy import stats
import os
from datetime import datetime
from dotenv import load_dotenv

# 1. CONEXIÓN Y CARGA DEL TABLÓN MAESTRO
ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.dirname(ruta_subcarpeta)
load_dotenv(dotenv_path=os.path.join(ruta_raiz, ".env"))

engine = create_engine(f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
print("Extrayendo el Tablón Maestro de Investigación...")
df = pd.read_sql("SELECT * FROM tablon_investigacion_oulad", con=engine)

# Configuración estética para publicaciones científicas
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 11, 'axes.labelsize': 12, 'axes.titlesize': 13})

print(f"Dataset cargado con éxito. Dimensiones: {df.shape[0]} filas, {df.shape[1]} columnas.\n")


# --- CONFIGURACIÓN DE LA CARPETA LOCAL DE GRÁFICOS ---
ruta_graficos = os.path.join(ruta_raiz, "Graficos")
if not os.path.exists(ruta_graficos):
    os.makedirs(ruta_graficos)
    print(f" Se ha creado la carpeta local: {ruta_graficos}")


# --- 2. AUDITORÍA Y FILTRADO CIENTÍFICO DE COMPORTAMIENTO DIGITAL ---
print("======================================================================")
print("FASE 1.1: ANÁLISIS DE VARIABILIDAD Y RELEVANCIA DE VARIABLES DIGITALES")
print("======================================================================")

columnas_clicks = [col for col in df.columns if col.startswith('clicks_')]
reporte_sparsity = []

for col in columnas_clicks:
    total_ceros = (df[col] == 0).sum()
    porcentaje_ceros = (total_ceros / len(df)) * 100
    varianza = df[col].var()
    reporte_sparsity.append({'Variable': col, 'Porcentaje_Ceros': porcentaje_ceros, 'Varianza': varianza})

df_sparsity = pd.DataFrame(reporte_sparsity).sort_values(by='Porcentaje_Ceros', ascending=False)
print(df_sparsity.to_string(index=False))

umbral_exclusion = 90.0
variables_a_descartar = df_sparsity[df_sparsity['Porcentaje_Ceros'] > umbral_exclusion]['Variable'].tolist()

print(f"\n Se descartan {len(variables_a_descartar)} variables por Sparsity extrema (> {umbral_exclusion}% de ceros).")
df_filtrado = df.drop(columns=variables_a_descartar)


# --- 3. VERIFICACIÓN DE SUPUESTOS Y EXPORTACIÓN INDIVIDUAL DE GRÁFICOS ---
print("\n======================================================================")
print("FASE 1.2: VERIFICACIÓN DE NORMALIDAD (KOLMOGOROV-SMIRNOV) Y RENDERIZACIÓN")
print("======================================================================")

variables_metricas = {
    'nota_promedio': 'Distribución de la Nota Promedio',
    'total_clicks_plataforma': 'Distribución del Volumen Total de Clics',
    'porcentaje_entregas_a_tiempo': 'Distribución del Porcentaje de Entregas a Tiempo'
}

reporte_normalidad = []
timestamp = datetime.now().strftime("%Y%m%d_%H%M")

for var, titulo in variables_metricas.items():
    data_var = df_filtrado[var].dropna()
    
    # Prueba de normalidad analítica (Z-score + K-S)
    data_std = (data_var - data_var.mean()) / data_var.std()
    stat, p_value = stats.kstest(data_std, 'norm')
    distribucion = "No Paramétrica (No Normal)" if p_value < 0.05 else "Paramétrica (Normal)"
    
    reporte_normalidad.append({
        'Variable': var,
        'Estadístico KS': stat,
        'p-valor': p_value,
        'Conclusión': distribucion
    })
    
    # --- RENDERIZACIÓN GRÁFICA INDIVIDUAL ---
    plt.figure(figsize=(7, 4.5))
    sns.histplot(data_var, kde=True, color='darkblue', stat="density", linewidth=1)
    
    # Formateo de alta calidad 
    plt.title(f"{titulo}\n(Prueba K-S p-value: {p_value:.4e})", pad=12)
    plt.xlabel("Escala Métrica de la Variable")
    plt.ylabel("Densidad Probabilística")
    plt.tight_layout()
    
    # Nombre cronológico individual
    nombre_imagen = f"distribucion_{var}_{timestamp}.png"
    ruta_salida = os.path.join(ruta_graficos, nombre_imagen)
    plt.savefig(ruta_salida, dpi=300)
    plt.close() # Cierra la figura actual para liberar memoria y no encimar los gráficos
    
    print(f"Gráfico individual exportado: Graficos/{nombre_imagen}")

# Mostrar el reporte consolidado en la terminal
print("\n")
df_norm = pd.DataFrame(reporte_normalidad)
print(df_norm.to_string(index=False))

print("Debido al comportamiento estrictamente No Paramétrico de todas las variables métricas,")
print("las evaluaciones de contraste grupal se realizarán mediante la prueba de Kruskal-Wallis.")