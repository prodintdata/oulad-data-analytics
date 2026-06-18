import matplotlib
matplotlib.use('Agg')  
import pandas as pd
import numpy as np
import os
from datetime import datetime
from sqlalchemy import create_engine
from scipy import stats
import scikit_posthocs as sp 
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv

# 1. CONEXIÓN Y CARGA LONGITUDINAL (SQL JOIN)
ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.dirname(ruta_subcarpeta)
load_dotenv(dotenv_path=os.path.join(ruta_raiz, ".env"))

engine = create_engine(f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")

print("Extrayendo histórico longitudinal de interacciones y resultados finales...")
# Extraemos el comportamiento día por día de cada alumno filtrando el ciclo lectivo oficial [0, 240]
query = """
    SELECT v.id_student, v.date, v.sum_click, i.final_result
    FROM studentvle v
    INNER JOIN studentinfo i ON v.id_student = i.id_student
    WHERE v.date >= 0 AND v.date <= 240
"""
df_crudo = pd.read_sql(query, con=engine)

# Configuración del entorno gráfico
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 10, 'axes.labelsize': 11, 'axes.titlesize': 12})
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
ruta_graficos = os.path.join(ruta_raiz, "Graficos")

# Parámetro global de significancia 
ALFA_TESIS = 0.01

# ======================================================================
# CONSTRUCCIÓN DE MÉTRICAS TEMPORALES
# ======================================================================
print("\nComputando métricas de consistencia temporal por cada estudiante...")

estudiantes_métricas = []

for id_estudiante, grupo in df_crudo.groupby('id_student'):
    resultado_final = grupo['final_result'].iloc[0]
    
    # Métrica A: Densidad de Conexión (% de días activos sobre el ciclo lectivo real)
    dias_activos = grupo['date'].nunique()
    densidad_conexion = (dias_activos / 241) * 100  # 241 días potenciales en el intervalo [0, 240]
    
    # Métrica B: Coeficiente de Variación (Estabilidad de clics en las sesiones)
    media_clics = grupo['sum_click'].mean()
    desviacion_clics = grupo['sum_click'].std()
    coef_variacion = (desviacion_clics / media_clics) if media_clics > 0 else 0
    
    estudiantes_métricas.append({
        'id_student': id_estudiante,
        'final_result': resultado_final,
        'densidad_conexion': densidad_conexion,
        'coef_variacion': coef_variacion
    })

df_temporal = pd.DataFrame(estudiantes_métricas)

# Estandarizamos las 3 cohortes fundamentales de la tesis
mapeo_cohortes = {
    'Pass': 'Cohorte_Exito', 'Distinction': 'Cohorte_Exito',
    'Fail': 'Cohorte_Riesgo',
    'Withdrawn': 'Cohorte_Desercion'
}
df_temporal['cohorte'] = df_temporal['final_result'].map(mapeo_cohortes)


# ======================================================================
# AUDITORÍA DE SUPUESTOS ESTADÍSTICOS Y SELECCIÓN  DEL MODELO
# ======================================================================
print("\n======================================================================")
print("REVISION DE SUPUESTOS Y ANÁLISIS LONGITUDINAL")
print("======================================================================")

# Aislamos los vectores de densidad por grupo para las pruebas
grupo_exito = df_temporal[df_temporal['cohorte'] == 'Cohorte_Exito']['densidad_conexion']
grupo_riesgo = df_temporal[df_temporal['cohorte'] == 'Cohorte_Riesgo']['densidad_conexion']
grupo_desercion = df_temporal[df_temporal['cohorte'] == 'Cohorte_Desercion']['densidad_conexion']

# --- 1. EVALUACIÓN DEL SUPUESTO DE NORMALIDAD  ---
def evaluar_normalidad(serie, nombre_grupo):
    n = len(serie)
    if n < 5000:
        # Para muestras pequeñas o medianas aplicamos Shapiro-Wilk
        _, p_norm = stats.shapiro(serie)
        print(f"  -> [{nombre_grupo}] evaluado con Shapiro-Wilk (n={n})")
    else:
        # Para muestras masivas escalamos a Kolmogorov-Smirnov usando Z-scores
        serie_estandarizada = (serie - serie.mean()) / serie.std()
        _, p_norm = stats.kstest(serie_estandarizada, 'norm')
        print(f"  -> [{nombre_grupo}] evaluado con Kolmogorov-Smirnov por volumen masivo (n={n})")
    return p_norm

print("Evaluando supuesto de normalidad en las muestras de datos...")
p_norm_exito = evaluar_normalidad(grupo_exito, "Cohorte Éxito")
p_norm_riesgo = evaluar_normalidad(grupo_riesgo, "Cohorte Riesgo")
p_norm_desercion = evaluar_normalidad(grupo_desercion, "Cohorte Deserción")

# Se asume normalidad si p > ALFA_TESIS (0.01) en todos los grupos
normalidad_valida = (p_norm_exito > ALFA_TESIS) and (p_norm_riesgo > ALFA_TESIS) and (p_norm_desercion > ALFA_TESIS)

# --- 2. EVALUACIÓN DEL SUPUESTO DE HOMOCEDASTICIDAD (Prueba de Levene) ---
_, p_levene = stats.levene(grupo_exito, grupo_riesgo, grupo_desercion)
homocedasticidad_valida = p_levene > ALFA_TESIS

# --- 3. PANEL DE DIAGNÓSTICO IMPRESO ---
print("\nDIAGNÓSTICO DE SUPUESTOS ESTADÍSTICOS:")
print(f"Normalidad p-valores -> Éxito: {p_norm_exito:.4e} | Riesgo: {p_norm_riesgo:.4e} | Deserción: {p_norm_desercion:.4e}")
print(f"Homocedasticidad p-valor (Levene): {p_levene:.4e}")
print(f"Nivel de significancia de control fijado (Alfa): {ALFA_TESIS}")

print("\n======================================================================")
print("REGLA DE DECISIÓN METODOLÓGICA:")
print("======================================================================")

if normalidad_valida and homocedasticidad_valida:
    print(f"TODOS LOS SUPUESTOS CUMPLIDOS (p > {ALFA_TESIS}): Distribución normal e igual varianza.")
    print("DECISIÓN: Se selecciona la prueba paramétrica [ANOVA DE UN FACTOR] y Post-Hoc de Tukey.")
    print("======================================================================\n")
    
    # Ejecución de ANOVA de un factor
    f_stat, p_global = stats.f_oneway(grupo_exito, grupo_riesgo, grupo_desercion)
    print(f"[RESULTADO EVALUACIÓN GLOBAL - ANOVA]:")
    print(f"Estadístico F: {f_stat:.4f}")
    print(f"p-valor Global: {p_global:.4e}\n")
    
    if p_global < ALFA_TESIS:
        print(f"RECHAZAR H0 (ANOVA): Existen diferencias significativas globales (p < {ALFA_TESIS}). Computando Tukey HSD...")
        from statsmodels.stats.multicomp import pairwise_tukeyhsd
        tukey = pairwise_tukeyhsd(endog=df_temporal['densidad_conexion'], groups=df_temporal['cohorte'], alpha=ALFA_TESIS)
        print(tukey)
        titulo_grafico = f"Densidad de Conexión al VLE según Cohorte\n(Modelación Paramétrica: ANOVA + Tukey HSD | alfa={ALFA_TESIS})"
else:
    print("SUPUESTOS VIOLADOS DETECTADOS:")
    if not normalidad_valida:
        print(f"  -> Al menos una cohorte rechaza la hipótesis de normalidad (p < {ALFA_TESIS}), exhibiendo la asimetría digital típica.")
    if not homocedasticidad_valida:
        print(f"  -> La prueba de Levene rechaza la igualdad de varianzas (p < {ALFA_TESIS}), confirmando heterocedasticidad inter-grupo.")
    
    print("\nDECISIÓN: Se descarta el uso de ANOVA por incumplimiento de supuestos de base.")
    print("SELECCIÓN: Se ejecuta la alternativa robusta no paramétrica [TEST DE KRUSKAL-WALLIS] y Post-Hoc de Dunn.")
    print("======================================================================\n")
    
    # Ejecución de Kruskal-Wallis
    h_stat, p_global = stats.kruskal(grupo_exito, grupo_riesgo, grupo_desercion)
    print(f"[RESULTADO EVALUACIÓN GLOBAL - KRUSKAL-WALLIS]:")
    print(f"Estadístico H de Kruskal-Wallis: {h_stat:.4f}")
    print(f"p-valor Global: {p_global:.4e}\n")
    
    if p_global < ALFA_TESIS:
        print(f"RECHAZAR H0 (Kruskal-Wallis): Existen diferencias significativas en la constancia de acceso (p < {ALFA_TESIS}).")
        print(f"Ejecutando Test Post-Hoc de Dunn con ajuste de Bonferroni (alfa local={ALFA_TESIS})...\n")
        
        matriz_dunn = sp.posthoc_dunn(df_temporal, val_col='densidad_conexion', group_col='cohorte', p_adjust='bonferroni')
        print("Matriz de p-valores del Test de Dunn (Ajustados por Bonferroni):")
        print(matriz_dunn)
        
        print("\n[Interpretación local de contrastes]:")
        cohortes_lista = list(matriz_dunn.index)
        for i in range(len(cohortes_lista)):
            for j in range(i + 1, len(cohortes_lista)):
                c1 = cohortes_lista[i]
                c2 = cohortes_lista[j]
                p_par = matriz_dunn.loc[c1, c2]
                if p_par < ALFA_TESIS:
                    print(f"  El contraste entre [{c1}] y [{c2}] es ALTAMENTE SIGNIFICATIVO (p = {p_par:.4e}). Son grupos conductualmente distintos.")
                else:
                    print(f"  El contraste entre [{c1}] y [{c2}] NO presenta diferencias significativas (p = {p_par:.4f}).")
        
        titulo_grafico = f"Densidad de Conexión al VLE según Cohorte\n(Modelación No Paramétrica: Kruskal-Wallis + Dunn | alfa={ALFA_TESIS})"


# ======================================================================
# BLOQUE DE GRAFICOS
# ======================================================================
print("\nGenerando set de gráficos estructurales...")

# --- ENTREGABLE 1: DIAGRAMA DE CAJA (BOXPLOT) DINÁMICO ---
plt.figure(figsize=(10, 6))
sns.boxplot(x='cohorte', y='densidad_conexion', data=df_temporal, 
            order=['Cohorte_Exito', 'Cohorte_Riesgo', 'Cohorte_Desercion'], 
            hue='cohorte', legend=False, palette='Set2')
plt.title(titulo_grafico)
plt.xlabel("Cohortes de Estudiantes")
plt.ylabel("Porcentaje de Días con Actividad (%)")
plt.tight_layout()

nombre_g1 = f"boxplot_densidad_temporal_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_g1), dpi=300)
plt.close()
print(f"Guardado Boxplot dinámico: Graficos/{nombre_g1}")


# --- ENTREGABLE 2: NUEVO GRÁFICO DE DENSIDAD CONDUCTUAL (KDE COMBINADO) ---
plt.figure(figsize=(10, 6))
sns.kdeplot(data=df_temporal, x='densidad_conexion', hue='cohorte', fill=True,
            hue_order=['Cohorte_Exito', 'Cohorte_Riesgo', 'Cohorte_Desercion'],
            palette='Set2', alpha=0.4, linewidth=2)
plt.title(f"Distribución de la Densidad de Conexión por Cohorte\n(Evidencia Visual de Asimetría y Heterocedasticidad | alfa={ALFA_TESIS})")
plt.xlabel("Porcentaje de Días con Actividad (%)")
plt.ylabel("Densidad de Probabilidad")
plt.xlim(0, 100)
plt.tight_layout()

nombre_g2 = f"densidad_conductual_cohortes_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_g2), dpi=300)
plt.close()
print(f"Guardado gráfico de densidad KDE: Graficos/{nombre_g2}")


# --- ENTREGABLE 3: CURVA LONGITUDINAL DE DEGRADACIÓN DIARIA ---
print("Generando curva de degradación temporal diaria...")
df_crudo['cohorte'] = df_crudo['final_result'].map(mapeo_cohortes)

# Computamos la media de clics agrupada por día calendario y cohorte
linea_tiempo = df_crudo.groupby(['date', 'cohorte'])['sum_click'].mean().reset_index()

plt.figure(figsize=(14, 6))
sns.lineplot(x='date', y='sum_click', hue='cohorte', data=linea_tiempo, 
             hue_order=['Cohorte_Exito', 'Cohorte_Riesgo', 'Cohorte_Desercion'], linewidth=1.5)
plt.yscale('log')  # Escala logarítmica para estabilizar la asimetría y varianza extrema de clics
plt.title(f"Trayectoria Temporal del Esfuerzo Digital Diario por Cohorte (Alfa de control de Tesis = {ALFA_TESIS})")
plt.xlabel("Línea de Tiempo del Semestre (Días Calendario)")
plt.ylabel("Media de Clics Diarios (Escala Logarítmica)")
plt.tight_layout()

nombre_g3 = f"linea_tiempo_degradacion_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_g3), dpi=300)
plt.close()
print(f"Guardada curva de desgaste longitudinal: Graficos/{nombre_g3}")