import matplotlib
matplotlib.use('Agg')
import pandas as pd
import numpy as np
import os
from datetime import datetime
from sqlalchemy import create_engine
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv


ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.dirname(ruta_subcarpeta)
load_dotenv(dotenv_path=os.path.join(ruta_raiz, ".env"))

engine = create_engine(f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")

print("Extrayendo y reconstruyendo las métricas OLS de los estudiantes...")
query = """
    SELECT v.id_student, v.date, v.sum_click, i.final_result
    FROM studentvle v
    INNER JOIN studentinfo i ON v.id_student = i.id_student
    WHERE v.date >= 0 AND v.date <= 168
"""
df_crudo = pd.read_sql(query, con=engine)

# Configuración del entorno
sns.set_theme(style="whitegrid")
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
ruta_graficos = os.path.join(ruta_raiz, "Graficos")

# Recuperar beta_0 y beta_1
df_crudo['semana'] = (df_crudo['date'] // 7) + 1
df_semanal = df_crudo.groupby(['id_student', 'semana', 'final_result'])['sum_click'].sum().reset_index()

mapeo_cohortes = {'Pass': 'Cohorte_Exito', 'Distinction': 'Cohorte_Exito', 'Fail': 'Cohorte_Riesgo', 'Withdrawn': 'Cohorte_Desercion'}
df_semanal['cohorte'] = df_semanal['final_result'].map(mapeo_cohortes)

datos_ols = []
for (id_est, cohorte), grupo in df_semanal.groupby(['id_student', 'cohorte']):
    if len(grupo) >= 4:
        slope, intercept, _, _, _ = stats.linregress(grupo['semana'].values, grupo['sum_click'].values)
        datos_ols.append({'id_student': id_est, 'cohorte': cohorte, 'beta_0': intercept, 'beta_1': slope})

df_features = pd.DataFrame(datos_ols)

# ======================================================================
#  K-MEANS CLUSTERING
# ======================================================================
print("\nPreparando matriz de características y normalizando variables...")
X = df_features[['beta_0', 'beta_1']].values

# Escalamiento estándar (Media=0, Varianza=1) crucial para algoritmos basados en distancias euclidianas
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# --- 1. DETERMINACIÓN DEL NÚMERO ÓPTIMO DE CLÚSTERES (MÉTODO DEL CODO) ---
print("Evaluando optimización de hiperparámetros (Inercia de K-Means)...")
inercias = []
rango_k = range(1, 8)
for k in rango_k:
    kmeans_test = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans_test.fit(X_scaled)
    inercias.append(kmeans_test.inertia_)

# Guardar Gráfico del Codo
plt.figure(figsize=(8, 4.5))
plt.plot(rango_k, inercias, 'bx-')
plt.xlabel('Número de Clústeres (K)')
plt.ylabel('Inercia / Distorsión WCSS')
plt.title('Método del Codo para Selección de K Óptimo en Perfiles de Estudiantes')
plt.tight_layout()
nombre_codo = f"kmeans_metodo_codo_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_codo), dpi=300)
plt.close()
print(f"Guardado gráfico de diagnóstico: Graficos/{nombre_codo}")

# --- 2. EJECUCIÓN DEL MODELO DEFINITIVO (Fijamos K=3 para contrastar las 3 cohortes) ---
K_ELEGIDO = 3
print(f"\nEntrenando modelo K-Means definitivo con K={K_ELEGIDO}...")
kmeans = KMeans(n_clusters=K_ELEGIDO, random_state=42, n_init=10)
df_features['cluster_matematico'] = kmeans.fit_predict(X_scaled)


df_features['cluster_label'] = df_features['cluster_matematico'].map(lambda x: f"Clúster {x}")

# ======================================================================
# ANÁLISIS DE CRUCE ENTRE COHORTES REALES Y CLÚSTERES MATEMÁTICOS
# ======================================================================
print("\n======================================================================")
print("MATRIZ DE CRUCE: COHORTES REALES VS. CLÚSTERES MATEMÁTICOS")
print("======================================================================")
matriz_cruce = pd.crosstab(df_features['cohorte'], df_features['cluster_label'], margins=False)
print(matriz_cruce)

print("\nPorcentajes de composición por cohorte dentro de cada clúster:")
matriz_porcentajes = pd.crosstab(df_features['cohorte'], df_features['cluster_label'], normalize='columns') * 100
print(matriz_porcentajes.round(2))

print("\n======================================================================")
print("DISTRIBUCIÓN INVERSA: DÓNDE SE UBICAN LAS COHORTES REALES EN LOS CLÚSTERES")
print("======================================================================")
matriz_inversa_porcentajes = pd.crosstab(df_features['cohorte'], df_features['cluster_label'], normalize='index') * 100
print(matriz_inversa_porcentajes.round(2))

# --- 3. VISUALIZACIÓN DEL ESPACIO DE REGLAS SEGÚN K-MEANS ---

plt.figure(figsize=(12, 7))

sns.scatterplot(data=df_features, x='beta_0', y='beta_1', hue='cluster_label',
                palette='Set1', alpha=0.5, s=20) 

plt.axhline(0, color='black', linestyle='--', linewidth=0.8)
plt.title(f"Segmentación Algorítmica K-Means (K={K_ELEGIDO}) basada en Coeficientes OLS\n(Población Completa: n={len(df_features)} estudiantes)")
plt.xlabel("Intercepto $\\beta_0$ (Impulso Inicial)")
plt.ylabel("Pendiente $\\beta_1$ (Coeficiente de Fatiga)")

plt.legend(title="Segmentos K-Means")
plt.tight_layout()

nombre_g_km = f"scatter_clusters_kmeans_completo_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_g_km), dpi=300)
plt.close()
print(f"\nGuardado Scatter Plot Completo con el 100% de la población: Graficos/{nombre_g_km}")