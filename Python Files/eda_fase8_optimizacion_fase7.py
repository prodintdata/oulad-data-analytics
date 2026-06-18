import matplotlib
matplotlib.use('Agg')
import pandas as pd
import numpy as np
import os
from datetime import datetime
from sqlalchemy import create_engine
from scipy import stats
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv

# 1. CONEXIÓN Y EXTRACCIÓN DE DATOS CRUDOS
ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.dirname(ruta_subcarpeta)
load_dotenv(dotenv_path=os.path.join(ruta_raiz, ".env"))

engine = create_engine(f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")

print("Extrayendo historial diario para cálculo de variables complejas...")
query = """
    SELECT v.id_student, v.date, v.sum_click, i.final_result
    FROM studentvle v
    INNER JOIN studentinfo i ON v.id_student = i.id_student
    WHERE v.date >= 0 AND v.date <= 168
"""
df_crudo = pd.read_sql(query, con=engine)

# Configuración estética
sns.set_theme(style="whitegrid")
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
ruta_graficos = os.path.join(ruta_raiz, "Graficos")

# 2. INGENIERÍA DE CARACTERÍSTICAS AVANZADA
df_crudo['semana'] = (df_crudo['date'] // 7) + 1
df_semanal = df_crudo.groupby(['id_student', 'semana', 'final_result'])['sum_click'].sum().reset_index()

print("Calculando Coeficiente de Variación y Racha Máxima de Inactividad por alumno...")
# Matriz base para almacenar las nuevas métricas
datos_avanzados = []

for id_est, grupo_diario in df_crudo.groupby('id_student'):
    # A) Racha Máxima de Inactividad
    dias_activos = sorted(grupo_diario['date'].unique())
    
    # Reconstruimos el vector completo de días del semestre (0 a 168) para medir ausencias consecutivas
    vector_presencia = np.zeros(169)
    vector_presencia[dias_activos] = 1
    
    # Algoritmo de conteo de rachas de ceros
    rachas_ceros = []
    racha_actual = 0
    for flag in vector_presencia:
        if flag == 0:
            racha_actual += 1
        else:
            if racha_actual > 0:
                rachas_ceros.append(racha_actual)
            racha_actual = 0
    if racha_actual > 0:
        rachas_ceros.append(racha_actual)
        
    max_racha = max(rachas_ceros) if len(rachas_ceros) > 0 else 0
    total_dias_activos = len(dias_activos)
    
    datos_avanzados.append({
        'id_student': id_est,
        'densidad_conexion': (total_dias_activos / 169) * 100,
        'max_racha_inactividad': max_racha
    })

df_avanzado = pd.DataFrame(datos_avanzados)

print("Calculando pendientes OLS y Coeficientes de Variación Semanal...")
datos_ols = []
for (id_est, final_res), grupo_sem in df_semanal.groupby(['id_student', 'final_result']):
    if len(grupo_sem) >= 4:
        # Pendiente e Intercepto
        slope, intercept, _, _, _ = stats.linregress(grupo_sem['semana'].values, grupo_sem['sum_click'].values)
        
        # B) Coeficiente de Variación (CV = std / mean)
        clics = grupo_sem['sum_click'].values
        mean_clics = np.mean(clics)
        cv = np.std(clics) / mean_clics if mean_clics > 0 else 0
        
        datos_ols.append({
            'id_student': id_est,
            'final_result': final_res,
            'beta_0_intercepto': intercept,
            'beta_1_pendiente': slope,
            'coef_variacion': cv
        })

df_ols = pd.DataFrame(datos_ols)

# Unificar todo el ecosistema de variables en el Dataset Maestro 
df_maestro = df_ols.merge(df_avanzado, on='id_student', how='inner')

# Mapeo del Target Operativo (SAT)
mapeo_cohortes = {'Pass': 'Cohorte_Exito', 'Distinction': 'Cohorte_Exito', 'Fail': 'Cohorte_Riesgo', 'Withdrawn': 'Cohorte_Desercion'}
df_maestro['cohorte'] = df_maestro['final_result'].map(mapeo_cohortes)
df_maestro['target_alerta'] = df_maestro['cohorte'].apply(lambda x: 0 if x == 'Cohorte_Exito' else 1)

# Variables Predictoras Optimizadas (5 Features en lugar de 3)
X = df_maestro[['beta_0_intercepto', 'beta_1_pendiente', 'densidad_conexion', 'coef_variacion', 'max_racha_inactividad']]
y = df_maestro['target_alerta']

# División balanceada idéntica para comparación justa
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)

print(f"\nTablón optimizado listo. Características evaluadas: {list(X.columns)}")

# ======================================================================
# ENTRENAMIENTO DEL MODELO OPTIMIZADO
# ======================================================================
print("Entrenando clasificador supervisado optimizado...")
modelo_opt = DecisionTreeClassifier(max_depth=6, min_samples_leaf=50, random_state=42, criterion='gini')
modelo_opt.fit(X_train, y_train)

y_pred = modelo_opt.predict(X_test)
y_prob = modelo_opt.predict_proba(X_test)[:, 1]

# ======================================================================
# REPORTES DE RENDIMIENTO DE LA OPTIMIZACIÓN
# ======================================================================
print("\n======================================================================")
print("INFORME DE RENDIMIENTO: SISTEMA DE ALERTA TEMPRANA OPTIMIZADO")
print("======================================================================")
print("\n[Nueva Matriz de Confusión]:")
cm = confusion_matrix(y_test, y_pred)
print(f"Verdaderos Negativos (Éxito correcto): {cm[0,0]}")
print(f"Falsos Positivos (Falsa Alerta): {cm[0,1]}")
print(f"Falsos Negativos (Peligro crítico omitido): {cm[1,0]}")
print(f"Verdaderos Positivos (Alerta efectiva de riesgo): {cm[1,1]}")

print("\n[Nuevas Métricas de Clasificación]:")
print(classification_report(y_test, y_pred, target_names=['Estable (0)', 'En Riesgo (1)']))

auc_opt = roc_auc_score(y_test, y_prob)
print(f"Nueva Capacidad de Discriminación Global (AUC-ROC): {auc_opt:.4f}")

# ======================================================================
# EXPORTACIÓN DE DIAGNÓSTICOS GRÁFICOS
# ======================================================================
# --- IMPORTANCIA DE VARIABLES OPTIMIZADA ---
plt.figure(figsize=(9, 5.5))
importancias = pd.Series(modelo_opt.feature_importances_, index=X.columns).sort_values(ascending=True)
importancias.plot(kind='barh', color='darkgreen')
plt.title("Gráfico de Importancia de Variables Optimizado\n(Feature Importance con Incorporación de CV y Rachas de Inactividad)")
plt.xlabel("Poder de Contribución Relativa al Modelo")
plt.tight_layout()
nombre_g1 = f"sat_opt_importancia_variables_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_g1), dpi=300)
plt.close()

# --- COMPARATIVA DE CURVA ROC ---
fpr, tpr, _ = roc_curve(y_test, y_prob)
plt.figure(figsize=(7, 6))
plt.plot(fpr, tpr, color='forestgreen', lw=2.5, label=f'Modelo Optimizado  (AUC = {auc_opt:.3f})')
plt.plot([0, 1], [0, 1], color='navy', lw=1, linestyle='--')
plt.xlabel('Tasa de Falsos Positivos')
plt.ylabel('Tasa de Verdaderos Positivos')
plt.title('Curva ROC - Optimización del Sistema Predictivo')
plt.legend(loc="lower right")
plt.tight_layout()
nombre_g2 = f"sat_opt_curva_roc_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_g2), dpi=300)
plt.close()
print(f"\nDiagnósticos gráficos guardados con éxito en la carpeta /Graficos.")