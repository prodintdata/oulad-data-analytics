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

# 1. CONEXIÓN Y CARGA DE DATOS COMBINADOS (SQL JOIN)
ruta_subcarpeta = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.dirname(ruta_subcarpeta)
load_dotenv(dotenv_path=os.path.join(ruta_raiz, ".env"))

engine = create_engine(f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")

print("Extrayendo interacciones del VLE cruzadas con la región del estudiante (SQL JOIN)...")
query = """
    SELECT v.code_module, v.code_presentation, v.date, v.sum_click, i.region
    FROM studentvle v
    INNER JOIN studentinfo i ON v.id_student = i.id_student
"""
df_vle = pd.read_sql(query, con=engine)

# Configuraciones de entorno y estética académica
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 10, 'axes.labelsize': 11, 'axes.titlesize': 12})
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
ruta_graficos = os.path.join(ruta_raiz, "Graficos")


# ======================================================================
# PARSER INTELIGENTE DE ARCHIVOS TEXTO PLANO DE LA MET OFFICE
# ======================================================================
print("\nProcesando y parseando archivos de texto plano de la Met Office...")

def parsear_met_office(nombre_archivo):
    ruta_txt = os.path.join(ruta_raiz, "Docs", nombre_archivo)
    if not os.path.exists(ruta_txt):
        raise FileNotFoundError(f"Falta el archivo meteorológico en la carpeta Docs: {ruta_txt}")
            
    dicc_clima = {}
    with open(ruta_txt, 'r', encoding='utf-8') as f:
        for linea in f:
            partes = linea.split()
            if len(partes) >= 4 and partes[0].isdigit() and partes[1].isdigit():
                anio = int(partes[0])
                mes = int(partes[1])
                if anio in [2013, 2014, 2015]:
                    try:
                        tmax_str = partes[2].replace('*', '').replace('#', '')
                        tmin_str = partes[3].replace('*', '').replace('#', '')
                        tmax = float(tmax_str)
                        tmin = float(tmin_str)
                        tmed = (tmax + tmin) / 2
                        dicc_clima[(anio, mes)] = tmed
                    except ValueError:
                        continue
    return dicc_clima

clima_heathrow = parsear_met_office("heathrowdata.txt")
clima_cardiff = parsear_met_office("cardiffdata.txt")
clima_bradford = parsear_met_office("bradforddata.txt")
clima_eskdalemuir = parsear_met_office("eskdalemuirdata.txt")

print("Archivos climáticos de la carpeta Docs cargados con éxito.")


# ======================================================================
# MAPEADOS GEOGRÁFICOS Y ASIGNACIÓN ADAPTATIVA DE TEMPERATURA
# ======================================================================
reglas_macro_regiones = {
    'London Region': 'Sur_Sureste', 'South East Region': 'Sur_Sureste', 'East Anglia': 'Sur_Sureste',
    'South West Region': 'Suroeste_Gales', 'Wales': 'Suroeste_Gales',
    'East Midlands': 'Centro_Norte', 'West Midlands': 'Centro_Norte', 'North West Region': 'Centro_Norte', 'Yorkshire Region': 'Centro_Norte', 'North Region': 'Centro_Norte',
    'Scotland': 'Escocia_Irlanda', 'Ireland': 'Escocia_Irlanda'
}

mapa_inicios = {
    '2013B': datetime(2013, 2, 1), '2013J': datetime(2013, 10, 1),
    '2014B': datetime(2014, 2, 1), '2014J': datetime(2014, 10, 1)
}

print("\nAsignando temperaturas dinámicas por macro-región y fecha calendario...")

def inyectar_clima_regional(row):
    pres = row['code_presentation']
    dias = int(row['date'])
    region_alumno = row['region']
    
    macro = reglas_macro_regiones.get(region_alumno)
    if pres in mapa_inicios and macro:
        fecha_real = mapa_inicios[pres] + pd.to_timedelta(dias, unit='D')
        llave_fecha = (fecha_real.year, fecha_real.month)
        
        if macro == 'Sur_Sureste':
            return clima_heathrow.get(llave_fecha, np.nan)
        elif macro == 'Suroeste_Gales':
            return clima_cardiff.get(llave_fecha, np.nan)
        elif macro == 'Centro_Norte':
            return clima_bradford.get(llave_fecha, np.nan)
        elif macro == 'Escocia_Irlanda':
            return clima_eskdalemuir.get(llave_fecha, np.nan)
            
    return np.nan

df_vle['temperatura_regional'] = df_vle.apply(inyectar_clima_regional, axis=1)
df_vle.dropna(subset=['temperatura_regional'], inplace=True)
df_vle['macro_region_txt'] = df_vle['region'].map(reglas_macro_regiones)

# ======================================================================
# SEGMENTACIÓN ADAPTATIVA POR CUARTILES SIMÉTRICOS (DUPLICATES='DROP')
# ======================================================================
print("\nSegmentando rangos de datos...")
etiquetas_temp = ['Temperatura Baja', 'Temperatura Media-Baja', 'Temperatura Media-Alta', 'Temperatura Alta']
etiquetas_clics = ['Clics Bajos', 'Clics Medios', 'Clics Altos', 'Clics Ultra Altos']

df_vle['rango_temperatura'] = pd.qcut(df_vle['temperatura_regional'], q=4, labels=etiquetas_temp, duplicates='drop')

cortes_clics = pd.qcut(df_vle['sum_click'], q=4, duplicates='drop')
num_intervalos = len(cortes_clics.cat.categories)

if num_intervalos == 4:
    df_vle['nivel_clics'] = pd.qcut(df_vle['sum_click'], q=4, labels=etiquetas_clics, duplicates='drop')
else:
    etiquetas_ajustadas = etiquetas_clics[-num_intervalos:]
    df_vle['nivel_clics'] = pd.qcut(df_vle['sum_click'], q=4, labels=etiquetas_ajustadas, duplicates='drop')


# --- GRÁFICO 1: VIOLÍN COMPARATIVO GLOBAL CONJUNTO (EL QUE YA TENÍAS) ---
print("\nGenerando set de gráficos estructurales...")
plt.figure(figsize=(14, 8))
sns.violinplot(x='rango_temperatura', y='sum_click', hue='macro_region_txt', data=df_vle, order=etiquetas_temp, palette='muted')
plt.yscale('log')
plt.title("Estructura Distribucional y Densidad de Clics Diarios por Rango Térmico y Macro-Región")
plt.xlabel("Rangos de Temperatura por Cuartil")
plt.ylabel("Volumen de Clics Diarios (Escala Logarítmica)")
plt.legend(title="Macro-Regiones Climáticas", loc='upper right')
plt.tight_layout()
nombre_g1 = f"violin_clics_macro_regiones_global_{timestamp}.png"
plt.savefig(os.path.join(ruta_graficos, nombre_g1), dpi=300)
plt.close()
print(f"Gráfico comparativo global guardado: Graficos/{nombre_g1}")


# --- NUEVA FUNCIÓN: GRÁFICOS DE VIOLÍN INDIVIDUALES EXCLUSIVOS POR REGIÓN ---
macro_zonas = df_vle['macro_region_txt'].unique()
colores_zonas = {'Escocia_Irlanda': 'snowflake', 'Sur_Sureste': 'deep', 'Suroeste_Gales': 'pastel', 'Centro_Norte': 'dark'}

for zona in macro_zonas:
    df_zona = df_vle[df_vle['macro_region_txt'] == zona]
    
    plt.figure(figsize=(9, 6))
    # Genera un gráfico limpio enfocado únicamente en la distribución interna de esa zona
    sns.violinplot(x='rango_temperatura', y='sum_click', data=df_zona, order=etiquetas_temp, color='skyblue' if zona=='Escocia_Irlanda' else 'salmon')
    plt.yscale('log')
    plt.title(f"Distribución de Densidad de Clics Diarios - Macro-Región: {zona.replace('_', ' y ')}")
    plt.xlabel("Rangos de Temperatura (Cuartiles Locales)")
    plt.ylabel("Volumen de Clics Diarios (Escala Logarítmica)")
    plt.tight_layout()
    
    nombre_v_individual = f"violin_individual_{zona}_{timestamp}.png"
    plt.savefig(os.path.join(ruta_graficos, nombre_v_individual), dpi=300)
    plt.close()
    print(f" Gráfico de Violín individual guardado: Graficos/{nombre_v_individual}")


# --- CONTRASTE ESTADÍSTICO GLOBAL ---
tabla_contingencia = pd.crosstab(df_vle['rango_temperatura'], df_vle['nivel_clics'])
chi2, p_valor, dof, esperados = stats.chi2_contingency(tabla_contingencia)

total_obs = tabla_contingencia.sum().sum()
min_dimension = min(tabla_contingencia.shape) - 1
v_cramer = np.sqrt(chi2 / (total_obs * min_dimension))

# Clasificación paramétrica industrial de la fuerza del efecto (V de Cramer)
if v_cramer < 0.10:
    fuerza_efecto = "Despreciable o Muy Débil"
elif v_cramer < 0.30:
    fuerza_efecto = "Débil"
elif v_cramer < 0.50:
    fuerza_efecto = "Moderada"
else:
    fuerza_efecto = "Fuerte"

print(f"\n[RESULTADOS DEL MODELO GLOBAL CONSOLIDADO]:")
print(f"Estructura de la Matriz: {tabla_contingencia.shape[0]}x{tabla_contingencia.shape[1]}")
print(f"p-valor Chi-cuadrado: {p_valor:.4e}")
print(f"Tamaño del efecto (V de Cramer): {v_cramer:.4f} -> Magnitud: [{fuerza_efecto}]")

# --- REGLA DE DECISIÓN AUTOMATIZADA CON ALFA = 0.01 ---
print("\n======================================================================")
print("DECISIÓN ESTADÍSTICA DEL MODELO GLOBAL:")
print("======================================================================")
if p_valor < 0.01:
    print(f"RECHAZAR HIPÓTESIS NULA (H0): El p-valor ({p_valor:.4e}) es menor que el nivel de significancia estricto alfa (0.01).")
    print(f"CONCLUSIÓN: Se demuestra de forma contundente que la temperatura regional percibida y el nivel de interacción")
    print(f"digital diaria NO son independientes. El factor climático influye significativamente en el comportamiento del alumno.")
    print(f"La fuerza de esta influencia es [{fuerza_efecto.upper()}], actuando como un condicionante ambiental secundario.")
    print("======================================================================\n")
    
    print("Procediendo al análisis post-hoc segmentado por macro-región...")
    
    # --- EVALUACIÓN DE RESIDUOS DE HABERMAN SEGMENTADA ---
    print("\n--- ANÁLISIS COMPORTAMENTAL POST-HOC POR MACRO-REGIÓN ---")
    macro_zonas = df_vle['macro_region_txt'].unique()
    for zona in macro_zonas:
        df_zona = df_vle[df_vle['macro_region_txt'] == zona]
        sub_tabla = pd.crosstab(df_zona['rango_temperatura'], df_zona['nivel_clics'])
        
        if sub_tabla.shape[0] > 1 and sub_tabla.shape[1] > 1:
            chi2_z, p_z, _, esp_z = stats.chi2_contingency(sub_tabla)
            res_z = (sub_tabla - esp_z) / np.sqrt(esp_z)
            
            print(f"\n> Análisis para Macro-Región: [{zona}] (p-val: {p_z:.4e})")
            for rt in res_z.index:
                for nc in res_z.columns:
                    z_val = res_z.loc[rt, nc]
                    if z_val > 2.58:
                        print(f"  • En [{rt}], el volumen de [{nc}] es ANÓMALAMENTE ALTO (Z = {z_val:.2f})")
                    elif z_val < -2.58:
                        print(f"  • En [{rt}], el volumen de [{nc}] es ANÓMALAMENTE BAJO (Z = {z_val:.2f})")
                        
            # --- MAPA DE CALOR DE RESIDUOS ---
            plt.figure(figsize=(8, 5))
            sns.heatmap(res_z, annot=True, cmap="RdBu_r", center=0, fmt=".2f", linewidths=0.5)
            plt.title(f"Residuos de Haberman (Z): Macro-Región {zona}\nValores fuera de [-2.58, 2.58] indican efectos significativos")
            plt.xlabel("Nivel de Clics Diarios")
            plt.ylabel("Rangos de Temperatura")
            plt.tight_layout()
            nombre_heatmap = f"heatmap_residuos_{zona}_{timestamp}.png"
            plt.savefig(os.path.join(ruta_graficos, nombre_heatmap), dpi=300)
            plt.close()
            print(f" Mapa de calor guardado: Graficos/{nombre_heatmap}")
else:
    print(f"NO RECHAZAR HIPÓTESIS NULA (H0): El p-valor ({p_valor:.4e}) es mayor o igual que alfa (0.01).")
    print(f"CONCLUSIÓN: No existe evidencia estadística suficiente para afirmar que el clima influya en las interacciones.")
    print(f"Las variables se consideran independientes en el marco analítico actual.")
    print("======================================================================\n")