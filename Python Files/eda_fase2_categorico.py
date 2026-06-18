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
df = pd.read_sql("SELECT code_module, code_presentation, final_result FROM tablon_investigacion_oulad", con=engine)

sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 10, 'axes.labelsize': 11, 'axes.titlesize': 12})

timestamp = datetime.now().strftime("%Y%m%d_%H%M")
ruta_graficos = os.path.join(ruta_raiz, "Graficos")


def calcular_v_cramer(tabla_contingencia, chi2):
    total_observaciones = tabla_contingencia.sum().sum()
    min_dimensiones = min(tabla_contingencia.shape) - 1
    v_cramer = np.sqrt(chi2 / (total_observaciones * min_dimensiones))
    
    # Escala estándar de interpretación científica
    if v_cramer < 0.10:
        fuerza = "Despreciable o muy débil"
    elif v_cramer < 0.30:
        fuerza = "Débil"
    elif v_cramer < 0.50:
        fuerza = "Moderada"
    else:
        fuerza = "Fuerte"
        
    return v_cramer, fuerza

# ======================================================================
# TESIS A PROBAR: ¿CUÁL ES EL MÓDULO CON MAYOR DESERCIÓN Y EN CUÁL 
# SEMESTRE DESERTARON O PASARON MÁS ESTUDIANTES?
# ======================================================================
print("======================================================================")
print("RESPUESTA A PREGUNTAS: ANÁLISIS DE FRECUENCIAS RELATIVAS")
print("======================================================================")

# Cálculo de porcentajes por Módulo
ct_modulo = pd.crosstab(df['code_module'], df['final_result'], normalize='index') * 100
modulo_max_desercion = ct_modulo['Withdrawn'].idxmax()
porcentaje_max_desercion = ct_modulo['Withdrawn'].max()
modulo_max_pasados = ct_modulo['Pass'].idxmax()
porcentaje_max_pasados = ct_modulo['Pass'].max()

print(f"1-) El módulo con mayor porcentaje de deserción es: {modulo_max_desercion} ({porcentaje_max_desercion:.2f}%).")
print(f"2-) El módulo con mayor porcentaje de aprobados es: {modulo_max_pasados} ({porcentaje_max_pasados:.2f}%).")

# Cálculo de porcentajes por Semestre
ct_semestre = pd.crosstab(df['code_presentation'], df['final_result'], normalize='index') * 100
semestre_max_desercion = ct_semestre['Withdrawn'].idxmax()
semestre_max_pasados = (ct_semestre['Pass'] + ct_semestre['Distinction']).idxmax()

print(f"3-) El semestre con mayor porcentaje de deserción es: {semestre_max_desercion} ({ct_semestre['Withdrawn'].max():.2f}%).")
print(f"4-) El semestre donde pasó un mayor porcentaje de estudiantes (Pass + Distinction) es: {semestre_max_pasados}.\n")

# --- RENDERIZACIÓN Y DESPLIEGUE DE GRÁFICOS ---
# Gráfico 1: Módulos
ax1 = ct_modulo.plot(kind='bar', stacked=True, figsize=(8, 5), color=['coral', 'crimson', 'darkgreen', 'royalblue'])
plt.title("Proporción del Resultado Final por Módulo Educativo")
plt.xlabel("Módulo")
plt.ylabel("Porcentaje (%)")
plt.legend(title="Resultado", bbox_to_anchor=(1.05, 1), loc='upper left')

# Ciclo automático para colocar los porcentajes dentro de cada barra
for c in ax1.containers:
    # label_type='center' coloca el texto en medio de cada segmento
    # fmt='%.1f%%' formatea el número con un decimal y el signo de %
    ax1.bar_label(c, label_type='center', fmt='%.1f%%', fontsize=9, color='white', weight='bold')

plt.tight_layout()
plt.savefig(os.path.join(ruta_graficos, f"proporcion_resultado_por_modulo_{timestamp}.png"), dpi=300)
plt.show()
plt.close()


# Gráfico 2: Semestres 
ax2 = ct_semestre.plot(kind='bar', stacked=True, figsize=(8, 5), color=['coral', 'crimson', 'darkgreen', 'royalblue'])
plt.title("Proporción del Resultado Final por Semestre Académico")
plt.xlabel("Semestre")
plt.ylabel("Porcentaje (%)")
plt.legend(title="Resultado", bbox_to_anchor=(1.05, 1), loc='upper left')

# Ciclo automático para los semestres
for c in ax2.containers:
    ax2.bar_label(c, label_type='center', fmt='%.1f%%', fontsize=9, color='white', weight='bold')

plt.tight_layout()
plt.savefig(os.path.join(ruta_graficos, f"proporcion_resultado_por_semestre_{timestamp}.png"), dpi=300)
plt.show()
plt.close()


# ======================================================================
# TESIS A PROBAR: ¿EXISTE RELACIÓN ESTADÍSTICAMENTE SIGNIFICATIVA ENTRE 
# EL MÓDULO CURSADO Y EL RESULTADO FINAL DEL ESTUDIANTE?
# (REGLA DE DECISIÓN: CHI-CUADRADO MEDIANTE P-VALOR CON ALFA = 0.01)
# ======================================================================
print("======================================================================")
print("TESIS: EVALUACIÓN DE INDEPENDENCIA Y POST-HOC (HABERMAN)")
print("======================================================================")

tabla_contingencia = pd.crosstab(df['code_module'], df['final_result'])
chi2, p_valor, dof, esperados = stats.chi2_contingency(tabla_contingencia)
v_cramer, fuerza = calcular_v_cramer(tabla_contingencia, chi2)

print(f"p-valor obtenido: {p_valor:.4e}")
print(f"Fuerza de la relación (V de Cramer): {v_cramer:.4f} ({fuerza})\n")

if p_valor < 0.01:
    print("[DECISIÓN ESTADÍSTICA]: p-valor < 0.01. Se rechaza la hipótesis nula.")
    print("El módulo influye significativamente en el rendimiento final.\n")
    
    # Cálculo de Residuos Estandarizados (Post-Hoc Haberman)
    residuos = (tabla_contingencia - esperados) / np.sqrt(esperados)
    umbral_critico = 2.58
    
    print("--- INTERPRETACIÓN POST-HOC DE LOGROS Y DESERCIONES CRÍTICAS (Z > 2.58 o Z < -2.58) ---")
    for modulo in residuos.index:
        for resultado in residuos.columns:
            val_residuo = residuos.loc[modulo, resultado]
            if val_residuo > umbral_critico:
                print(f"En el módulo [{modulo}], el resultado [{resultado}] ocurre SIGNIFICATIVAMENTE MÁS de lo esperado (Z = {val_residuo:.2f}).")
            elif val_residuo < -umbral_critico:
                print(f"En el módulo [{modulo}], el resultado [{resultado}] ocurre SIGNIFICATIVAMENTE MENOS de lo esperado (Z = {val_residuo:.2f}).")
    
    # Gráfico 3: Mapa de Calor
    plt.figure(figsize=(9, 5))
    sns.heatmap(residuos, annot=True, cmap="RdBu_r", center=0, fmt=".2f", linewidths=0.5)
    plt.title("Mapa de Calor de Residuos Estandarizados (Haberman)")
    plt.xlabel("Resultado Final")
    plt.ylabel("Módulo")
    plt.tight_layout()
    plt.savefig(os.path.join(ruta_graficos, f"heatmap_residuos_modulo_resultado_{timestamp}.png"), dpi=300)
    plt.show() # Muestra en pantalla
    plt.close()
else:
    print("[DECISIÓN ESTADÍSTICA]: No se rechaza la hipótesis nula. Variables independientes.")