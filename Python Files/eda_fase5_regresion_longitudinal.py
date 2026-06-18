import matplotlib
matplotlib.use('Agg')
import pandas as pd
import numpy as np
import os
from datetime import datetime
from sqlalchemy import create_engine
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv

# 1. CONEXIÓN Y CARGA DE TRAZAS LONGITUDINALES
ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.dirname(ruta_subcarpeta)
load_dotenv(dotenv_path=os.path.join(ruta_raiz, ".env"))

engine = create_engine(f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")

print("Extrayendo historial longitudinal diario para agregación semanal...")
query = """
    SELECT v.id_student, v.date, v.sum_click, i.final_result
    FROM studentvle v
    INNER JOIN studentinfo i ON v.id_student = i.id_student
    WHERE v.date >= 0 AND v.date <= 168
"""
# Limitamos a los primeros 168 días (Semanas 0 a 24) para estandarizar la ventana de observación
df_crudo = pd.read_sql(query, con=engine)

# Configuración estética académica
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 10, 'axes.labelsize': 11, 'axes.titlesize': 12})
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
ruta_graficos = os.path.join(ruta_raiz, "Graficos")

ALFA_TESIS = 0.01

# Homologación de las 3 cohortes metodológicas
mapeo_cohortes = {
    'Pass': 'Cohorte_Exito', 'Distinction': 'Cohorte_Exito',
    'Fail': 'Cohorte_Riesgo', 'Withdrawn': 'Cohorte_Desercion'
}
df_crudo['cohorte'] = df_crudo['final_result'].map(mapeo_cohortes)

# ======================================================================
# AGREGACIÓN SEMANAL Y AJUSTE OLS
# ======================================================================
print("\nTransformando escala temporal a semanas calendario...")
# Mapeamos los días relativos a semanas enteras (Día 0-6 -> Semana 1, Día 7-13 -> Semana 2, etc.)
df_crudo['semana'] = (df_crudo['date'] // 7) + 1

print("Calculando agregados semanales por estudiante...")
df_semanal = df_crudo.groupby(['id_student', 'semana', 'cohorte'])['sum_click'].sum().reset_index()

print("Ajustando modelos de Regresión Lineal OLS individuales por alumno...")
coeficientes_estudiantes = []

for (id_estudiante, cohorte), grupo in df_semanal.groupby(['id_student', 'cohorte']):
    # Forzamos que el alumno tenga al menos 4 semanas con interacciones para calcular una tendencia real
    if len(grupo) >= 4:
        X = grupo['semana'].values
        Y = grupo['sum_click'].values
        
        # Ajustamos la recta de regresión lineal para este estudiante específico
        slope, intercept, r_value, p_value, std_err = stats.linregress(X, Y)
        
        coeficientes_estudiantes.append({
            'id_student': id_estudiante,
            'cohorte': cohorte,
            'beta_0_intercepto': intercept,
            'beta_1_pendiente': slope,
            'r_cuadrado': r_value**2
        })

df_regresion = pd.DataFrame(coeficientes_estudiantes)

print(f"Modelos OLS calculados con éxito para {len(df_regresion)} estudiantes.")


# ======================================================================
# EVALUACIÓN INFERENCIAL DE LAS PENDIENTES CONDUCTUALES
# ======================================================================
print("\n======================================================================")
print("FASE 5 EDA: EVALUACIÓN INFERENCIAL DE TENDENCIAS DE REGRESIÓN")
print("======================================================================")

# Aislamos las pendientes (Beta_1) por cohorte para verificar si difieren estadísticamente
p_exito = df_regresion[df_regresion['cohorte'] == 'Cohorte_Exito']['beta_1_pendiente']
p_riesgo = df_regresion[df_regresion['cohorte'] == 'Cohorte_Riesgo']['beta_1_pendiente']
p_desercion = df_regresion[df_regresion['cohorte'] == 'Cohorte_Desercion']['beta_1_pendiente']

# Aplicamos Kruskal-Wallis como contraste global para las pendientes por su alta dispersión
h_stat, p_global = stats.kruskal(p_exito, p_riesgo, p_desercion)
print(f"[EVALUACIÓN GLOBAL DE LAS PENDIENTES (BETA 1)]:")
print(f"Estadístico H de Kruskal-Wallis: {h_stat:.4f}")
print(f"p-valor Global: {p_global:.4e}")

print("\n======================================================================")
print("REGLA DE DECISIÓN DE LA FASE 5:")
print("======================================================================")
if p_global < ALFA_TESIS:
    print(f"RECHAZAR H0: Las pendientes de tracción o fatiga temporal varían significativamente según la cohorte académica.")
    print("La trayectoria del esfuerzo digital semanal es un factor diferenciador intrínseco.")
    
    # Medias de los coeficientes para sustentar el análisis cuantitativo
    resumen_medias = df_regresion.groupby('cohorte')[['beta_0_intercepto', 'beta_1_pendiente', 'r_cuadrado']].mean()
    print("\n[Valores Promedio de las Ecuaciones de Comportamiento por Cohorte]:")
    print(resumen_medias)
else:
    print("NO RECHAZAR H0: No se detectan diferencias significativas en el ritmo de degradación lineal.")


# ======================================================================
# GRAFICOS (ENTREGABLES FASE 5)
# ======================================================================
print("\nGenerando set de gráficos de modelación longitudinal...")

# --- ENTREGABLE 1: RECTAS DE TENDENCIA PROMEDIO POR COHORTE ---
plt.figure(figsize=(11, 6))
semanas_proyeccion = np.array([1, 24])

for cohorte in ['Cohorte_Exito', 'Cohorte_Riesgo', 'Cohorte_Desercion']:
    sub_df = df_regresion[df_regresion['cohorte'] == cohorte]
    b0_medio = sub_df['beta_0_intercepto'].mean()
    b1_medio = sub_df['beta_1_pendiente'].mean()
    
    # Calculamos los puntos de la recta idealizada
    y_recta = b0_medio + b1_medio * semanas_proyeccion
    
    # Graficamos la recta promedio del grupo
    plt.plot(semanas_proyeccion, y_recta, label=f"{cohorte} (Media $\\beta_1$: {b1_medio:.2f})", linewidth=3)

plt.title("Ecuaciones de Trayectoria Conductual Promedio por Cohorte\n(Modelación mediante Ajustes Lineales OLS Agregados)")
plt.xlabel("Semanas Transcurridas del Semestre")
plt.ylabel("Volumen Estimado de Clics Semanales")
plt.xlim(1, 24)
plt.xticks(range(1, 25, 2))
plt.legend(title="Cohortes Académicas")
plt.tight_layout()

nombre_g1 = f"rectas_tendencia_ols_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_g1), dpi=300)
plt.close()
print(f"Guardado mapa de rectas OLS promedio: Graficos/{nombre_g1}")


# --- ENTREGABLE 2: SCATTER PLOT BI-VARIADO (INTERCEPTO VS PENDIENTE) ---
plt.figure(figsize=(12, 7))
# Muestreamos si la cantidad de puntos afecta la visualización para evitar sobresaturación espacial
df_scatter = df_regresion.sample(min(3000, len(df_regresion)), random_state=42)

sns.scatterplot(data=df_scatter, x='beta_0_intercepto', y='beta_1_pendiente', hue='cohorte',
                hue_order=['Cohorte_Exito', 'Cohorte_Riesgo', 'Cohorte_Desercion'],
                palette='Set2', alpha=0.6, s=25)

plt.axhline(0, color='black', linestyle='--', linewidth=0.8) # Línea horizonte cero fatiga
plt.title("Estructura Bi-variada del Comportamiento Digital: Impulso Inicial ($\\beta_0$) vs. Coeficiente de Fatiga ($\\beta_1$)")
plt.xlabel("Intercepto $\\beta_0$ (Impulso / Intensidad Inicial de Clics)")
plt.ylabel("Pendiente $\\beta_1$ (Coeficiente de Fatiga o Aceleración Semanal)")

# Ajustamos límites para limpiar outliers extremos de visualización y ver la concentración central
plt.xlim(sub_df['beta_0_intercepto'].quantile(0.01), df_regresion['beta_0_intercepto'].quantile(0.95))
plt.ylim(df_regresion['beta_1_pendiente'].quantile(0.05), df_regresion['beta_1_pendiente'].quantile(0.95))
plt.legend(title="Cohortes")
plt.tight_layout()

nombre_g2 = f"scatter_bi_variado_ols_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_g2), dpi=300)
plt.close()
print(f"Guardado Scatter Plot bi-variado conductual: Graficos/{nombre_g2}")