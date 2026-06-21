import matplotlib
matplotlib.use('Agg')
import pandas as pd
import numpy as np
import os
from datetime import datetime
from sqlalchemy import create_engine
from scipy import stats
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv

# 1. CONEXIÓN Y EXTRACCIÓN DE TODO EL PIPELINE CONDUCTUAL
ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.dirname(ruta_subcarpeta)
load_dotenv(dotenv_path=os.path.join(ruta_raiz, ".env"))

engine = create_engine(f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")

print("Construyendo tablón maestro unificado...")
query = """
    SELECT v.id_student, v.date, v.sum_click, i.final_result
    FROM studentvle v
    INNER JOIN studentinfo i ON v.id_student = i.id_student
    WHERE v.date >= 0 AND v.date <= 168
"""
df_crudo = pd.read_sql(query, con=engine)

# Configuración de estilo para gráficos
sns.set_theme(style="whitegrid")
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
ruta_graficos = os.path.join(ruta_raiz, "Graficos")

# Procesamiento temporal
df_crudo['semana'] = (df_crudo['date'] // 7) + 1

print("Calculando métricas de Consistencia  y Tendencia Lineal OLS...")
# Agrupaciones base
df_semanal = df_crudo.groupby(['id_student', 'semana', 'final_result'])['sum_click'].sum().reset_index()
df_diario_count = df_crudo.groupby(['id_student'])['date'].nunique().reset_index(name='dias_activos')

mapeo_cohortes = {'Pass': 'Cohorte_Exito', 'Distinction': 'Cohorte_Exito', 'Fail': 'Cohorte_Riesgo', 'Withdrawn': 'Cohorte_Desercion'}
df_semanal['cohorte'] = df_semanal['final_result'].map(mapeo_cohortes)

registros_estudiantes = []
for (id_est, cohorte), grupo in df_semanal.groupby(['id_student', 'cohorte']):
    if len(grupo) >= 4:
        slope, intercept, _, _, _ = stats.linregress(grupo['semana'].values, grupo['sum_click'].values)
        registros_estudiantes.append({
            'id_student': id_est,
            'cohorte': cohorte,
            'beta_0_intercepto': intercept,
            'beta_1_pendiente': slope
        })

df_features = pd.DataFrame(registros_estudiantes)
# Integrar la Densidad de Conexión: total días activos / 169 días de la ventana
df_features = df_features.merge(df_diario_count, on='id_student', how='inner')
df_features['densidad_conexion'] = (df_features['dias_activos'] / 169) * 100

# ======================================================================
# CONFIGURACIÓN DE TARGET OPERATIVO (SISTEMA DE ALERTA TEMPRANA)
# ======================================================================
# 0 = Éxito Sostenible, 1 = Alerta Institucional (Riesgo o Deserción)
df_features['target_alerta'] = df_features['cohorte'].apply(lambda x: 0 if x == 'Cohorte_Exito' else 1)

X = df_features[['beta_0_intercepto', 'beta_1_pendiente', 'densidad_conexion']]
y = df_features['target_alerta']

# División balanceada de datos
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)

print(f"\nDataset listo. Entrenamiento: {X_train.shape[0]} alumnos. Prueba: {X_test.shape[0]} alumnos.")

# ======================================================================
# ENTRENAMIENTO DEL ÁRBOL DE DECISIÓN SUPERVISADO (SISTEMA DE ALERTA TEMPRANA - SAT)
# ======================================================================
print("\nEntrenando clasificador supervisado...")
modelo_sat = DecisionTreeClassifier(max_depth=6, min_samples_leaf=50, random_state=42, criterion='gini')
modelo_sat.fit(X_train, y_train)

# Predicciones
y_pred = modelo_sat.predict(X_test)
y_prob = modelo_sat.predict_proba(X_test)[:, 1]

# ======================================================================
# REPORTES DE RENDIMIENTO
# ======================================================================
print("\n======================================================================")
print("INFORME DE RENDIMIENTO DEL SISTEMA DE ALERTA TEMPRANA (SAT)")
print("======================================================================")
print("\n[Matriz de Confusión Real vs. Predicción]:")
cm = confusion_matrix(y_test, y_pred)
print(f"Verdaderos Negativos (Éxito predicho correctamente): {cm[0,0]}")
print(f"Falsos Positivos (Falsa Alerta - Alumno estable marcado en riesgo): {cm[0,1]}")
print(f"Falsos Negativos (Peligro crítico - Alumno en riesgo no detectado): {cm[1,0]}")
print(f"Verdaderos Positivos (Alerta efectiva - Estudiante en riesgo detectado): {cm[1,1]}")

print("\n[Métricas de Clasificación]:")
print(classification_report(y_test, y_pred, target_names=['Estable (0)', 'En Riesgo (1)']))

auc = roc_auc_score(y_test, y_prob)
print(f"Capacidad de Discriminación Global (AUC-ROC): {auc:.4f}")

# ======================================================================
# GRÁFICOS
# ======================================================================

print("\nGenerando mapa de calor para la Matriz de Confusión...")

etiquetas_heatmap = np.array([
    [f"Verdaderos Negativos\n(Éxito Correcto)\n{cm[0,0]}", f"Falsos Positivos\n(Falsa Alerta)\n{cm[0,1]}"],
    [f"Falsos Negativos\n(Peligro Omitido)\n{cm[1,0]}", f"Verdaderos Positivos\n(Alerta Efectiva)\n{cm[1,1]}"]
])

plt.figure(figsize=(7.5, 5.5))
sns.set_theme(style="white")

sns.heatmap(cm, annot=etiquetas_heatmap, fmt="", cmap="Oranges", cbar=True,
            xticklabels=['Predicción Estable (0)', 'Predicción Riesgo (1)'],
            yticklabels=['Estatus Real Estable (0)', 'Estatus Real Riesgo (1)'],
            annot_kws={"fontsize": 10, "weight": "bold"})

plt.title("Matriz de Confusión - Modelo Base (EDA 7)", fontsize=11, pad=15)
plt.xlabel("Predicción del Sistema (SAT)", fontsize=10, labelpad=8)
plt.ylabel("Realidad Académica del Estudiante", fontsize=10, labelpad=8)
plt.tight_layout()

nombre_cm_base = f"sat_base_matriz_confusion_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_cm_base), dpi=300)
plt.close()
print(f"[OK] Mapa de calor exportado exitosamente en: Graficos/{nombre_cm_base}")

sns.set_theme(style="whitegrid")

print("\nGenerando gráficos de diagnóstico predictivo...")

# --- IMPORTANCIA DE VARIABLES ---
plt.figure(figsize=(8, 5))
importancias = pd.Series(modelo_sat.feature_importances_, index=X.columns).sort_values(ascending=True)
importancias.plot(kind='barh', color='teal')
plt.title("Gráfico de Importancia de Variables en la Detección de Riesgo\n(Feature Importance - Algoritmo SAT)")
plt.xlabel("Poder de Contribución Relativa al Modelo")
plt.tight_layout()
nombre_g1 = f"sat_importancia_variables_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_g1), dpi=300)
plt.close()
print(f"Guardado gráfico de importancia: Graficos/{nombre_g1}")

# --- CURVA ROC ---
fpr, tpr, _ = roc_curve(y_test, y_prob)
plt.figure(figsize=(7, 6))
plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'Curva SAT (AUC = {auc:.3f})')
plt.plot([0, 1], [0, 1], color='navy', lw=1.5, linestyle='--')
plt.xlabel('Tasa de Falsos Positivos (1 - Especificidad)')
plt.ylabel('Tasa de Verdaderos Positivos (Sensibilidad / Recall)')
plt.title('Curva Característica Operativa del Receptor (ROC)')
plt.legend(loc="lower right")
plt.tight_layout()
nombre_g2 = f"sat_curva_roc_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_g2), dpi=300)
plt.close()
print(f"Guardado gráfico Curva ROC: Graficos/{nombre_g2}")