import os
import numpy as np
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine
from scipy.stats import kstest, levene
from scipy.spatial.distance import pdist, squareform
from sklearn.model_selection import train_test_split
from sklearn.manifold import MDS
import matplotlib.pyplot as plt
import seaborn as sns
from skbio.stats.distance import permanova
from skbio import DistanceMatrix  

def ejecutar_analisis_multivariante_permanova():
    # ==============================================================================
    # 1. CONEXIÓN A LA BASE DE DATOS Y EXTRACCIÓN DEL TABLÓN MAESTRO
    # ==============================================================================
    load_dotenv()

    usuario = os.getenv("DB_USER")
    contrasena = os.getenv("DB_PASSWORD")
    servidor = os.getenv("DB_HOST")
    base_datos = os.getenv("DB_NAME")
    
    
    puerto_env = os.getenv("DB_PORT")
    puerto = int(puerto_env) if puerto_env is not None else 3306
    
    engine = create_engine(f"mysql+pymysql://{usuario}:{contrasena}@{servidor}:{puerto}/{base_datos}")
    tabla_origen = "tablon_investigacion_oulad"
    
    print(f"Conexión exitosa. Extrayendo datos reales desde '{tabla_origen}'...")
    df_master = pd.read_sql(f"SELECT * FROM {tabla_origen}", con=engine)
    print(f"Población total detectada: {df_master.shape[0]} registros estudiantiles.")

    variables_y = ['total_clicks_plataforma', 'nota_promedio', 'porcentaje_entregas_a_tiempo']
    columna_grupo = 'final_result' 

    
    sns.set_theme(style="whitegrid")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    
    ruta_graficos = os.path.join(os.getcwd(), "Graficos")
    if not os.path.exists(ruta_graficos):
        os.makedirs(ruta_graficos)

    # Filtrar registros nulos en la variable objetivo 
    df_filtrado = df_master[df_master[columna_grupo].notna()].copy()

    # ==============================================================================
    # 2. OPTIMIZACIÓN DE MEMORIA: MUESTREO ESTRATIFICADO REPRESENTATIVO
    # ==============================================================================
    print("\n[INFO] Seleccionando Muestras para Mejorar Arquitectura de memoria...")
    tamano_muestra = 3000 
    
    df_muestra, _ = train_test_split(
        df_filtrado, 
        train_size=tamano_muestra, 
        stratify=df_filtrado[columna_grupo], 
        random_state=42
    )
    print(f"Muestra estratificada optimizada con éxito a n = {df_muestra.shape[0]} estudiantes.")

    # ==============================================================================
    # 3. AUDITORÍA ESTADÍSTICA DE SUPUESTOS
    # ==============================================================================
    print("\n" + "=" * 75)
    print(" FASE 1: AUDITORÍA DE SUPUESTOS PARAMÉTRICOS ")
    print("=" * 75)

    print("\n[A] Evaluando Normalidad de Variables Dependientes (Test Kolmogorov-Smirnov):")
    for var in variables_y:
        datos_estandarizados = (df_muestra[var] - df_muestra[var].mean()) / df_muestra[var].std()
        stat, p_val = kstest(datos_estandarizados, 'norm')
        status = "RECHAZADA (No es Normal)" if p_val < 0.01 else "ACEPTADA (Es Normal)"
        print(f"  * {var:<30} -> p-value: {p_val:.5e} | Distribución Normal: {status}")

    print("\n[B] Evaluando Homogeneidad de Varianzas Inter-grupo (Test de Levene):")
    grupos_unicos = df_muestra[columna_grupo].unique()
    for var in variables_y:
        listas_grupos = [df_muestra[df_muestra[columna_grupo] == g][var] for g in grupos_unicos]
        stat, p_val = levene(*listas_grupos)
        status = "RECHAZADA (Heterocedástico)" if p_val < 0.01 else "ACEPTADA (Homocedástico)"
        print(f"  * {var:<30} -> p-value: {p_val:.5e} | Varianzas Iguales: {status}")

    # ==============================================================================
    # 4. CONTRASTE MULTIVARIANTE GLOBAL (PERMANOVA GLOBAL)
    # ==============================================================================
    print("\n" + "=" * 75)
    print(" FASE 2: CONTRASTE MULTIVARIANTE GLOBAL (PERMANOVA) ")
    print("=" * 75)

    X = df_muestra[variables_y].values
    grupos_lista = df_muestra[columna_grupo].astype(str).tolist()

    # Formateo de índices compuestos únicos
    df_muestra['id_unico_registro'] = (
        df_muestra['id_student'].astype(str) + "_" + 
        df_muestra['code_module'].astype(str) + "_" + 
        df_muestra['code_presentation'].astype(str)
    )
    lista_ids_unicos = df_muestra['id_unico_registro'].tolist()

    print("Construyendo y formateando matriz de distancias...")
    dist_raw = squareform(pdist(X, metric='euclidean'))
    matriz_distancias = DistanceMatrix(dist_raw, ids=lista_ids_unicos)

    print("Corriendo permutaciones aleatorias (9,999 ciclos sobre la muestra)...")
    res_global = permanova(matriz_distancias, grupos_lista, permutations=9999)

    print("\n=== RESULTADOS DEL CONTRASTE GLOBAL ===")
    print(f" Estadístico de Separación (Pseudo-F) : {res_global['test statistic']:.4f}")
    print(f" Valor de Significancia (p-value)    : {res_global['p-value']:.5e}")
    print(f" Número de Permutaciones Ejecutadas   : {res_global['number of permutations']}")

    if res_global['p-value'] < 0.01:
        print("\nDECISIÓN ESTADÍSTICA:")
        print(f"p-value < 0.01. Se RECHAZA la Hipótesis Nula (H0).")
        print("El perfil combinado de clics, notas y puntualidad difiere entre los grupos.")
        
        # ==============================================================================
        # 5. ANÁLISIS POST-HOC POR PAREJAS (PAIRWISE PERMANOVA)
        # ==============================================================================
        print("\n" + "=" * 75)
        print(" FASE 3: ANÁLISIS POST-HOC POR PAREJAS (CORRECCIÓN DE BONFERRONI) ")
        print("=" * 75)
        
        from itertools import combinations
        parejas_posibles = list(combinations(grupos_unicos, 2))
        n_comparaciones = len(parejas_posibles)
        
        print(f"Ejecutando {n_comparaciones} contrastes locales por parejas...")
        print(f"{'Comparación':<30} | {'Pseudo-F':<10} | {'p-value Puro':<12} | {'p-value Adj (Bonferroni)':<25} | {'Significativo'}")
        print("-" * 110)
        
        for g1, g2 in parejas_posibles:
            df_sub = df_muestra[df_muestra[columna_grupo].isin([g1, g2])].copy()
            X_sub = df_sub[variables_y].values
            grupos_sub = df_sub[columna_grupo].astype(str).tolist()
            
            df_sub['id_unico_registro_sub'] = (
                df_sub['id_student'].astype(str) + "_" + 
                df_sub['code_module'].astype(str) + "_" + 
                df_sub['code_presentation'].astype(str)
            )
            lista_ids_sub = df_sub['id_unico_registro_sub'].tolist()
            
            dist_sub_raw = squareform(pdist(X_sub, metric='euclidean'))
            matriz_dist_sub = DistanceMatrix(dist_sub_raw, ids=lista_ids_sub)
            
            res_sub = permanova(matriz_dist_sub, grupos_sub, permutations=9999)
            
            p_puro = res_sub['p-value']
            p_adj = min(p_puro * n_comparaciones, 1.0)
            es_sig = "SÍ (p < 0.01)" if p_adj < 0.01 else "NO"
            
            label = f"{g1} vs {g2}"
            print(f"{label:<30} | {res_sub['test statistic']:<10.4f} | {p_puro:<12.5e} | {p_adj:<25.5e} | {es_sig}")
        print("=" * 110)

        # ==============================================================================
        # 6. FASE 4: VISUALIZACIÓN GRÁFICA MULTIDIMENSIONAL (PCoA / MDS)
        # ==============================================================================
        print("\n" + "=" * 75)
        print(" FASE 4: GENERANDO GRÁFICO DE ORDENACIÓN MULTIDIMENSIONAL (MDS) ")
        print("=" * 75)
        
        print("Proyectando el espacio multidimensional a 2D (Calculando MDS)...")
        mds = MDS(n_components=2, dissimilarity='precomputed', random_state=42, n_jobs=-1)
        componentes_2d = mds.fit_transform(dist_raw)

        df_grafico = pd.DataFrame(componentes_2d, columns=['Dimensión 1', 'Dimensión 2'])
        df_grafico['Cohorte'] = grupos_lista

        # Definimos una paleta de colores fija para que coincidan puntos y centroides
        paleta_colores = {'Pass':  '#66c2a5', 'Distinction': '#fc8d62', 'Fail': '#8da0cb', 'Withdrawn': '#e78ac3'}

        plt.figure(figsize=(10, 7))
        sns.scatterplot(
            x='Dimensión 1', 
            y='Dimensión 2', 
            hue='Cohorte', 
            palette=paleta_colores, 
            data=df_grafico, 
            alpha=0.5, 
            s=40,
            edgecolor='w',
            linewidth=0.5
        )

        for cohorte in df_grafico['Cohorte'].unique():
            centroide = df_grafico[df_grafico['Cohorte'] == cohorte][['Dimensión 1', 'Dimensión 2']].mean()
            
            plt.scatter(
                centroide['Dimensión 1'], centroide['Dimensión 2'], 
                marker='X', 
                s=280, 
                color=paleta_colores[cohorte], 
                edgecolor='black', 
                linewidth=1.5,
                label=f'Centroide {cohorte}'
            )

        plt.title("Mapa de Ordenación Multidimensional (MDS)\nVisualización de la Distancia Conductual y Académica entre Cohortes", fontsize=12, pad=15)
        plt.xlabel("Dimensión Principal 1 (Eje de Máxima Variabilidad)", fontsize=11)
        plt.ylabel("Dimensión Principal 2", fontsize=11)
        plt.legend(title="Grupos Estudiantiles y Centroides", bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()

        nombre_grafico_mds = f"permanova_mds_distancias_{timestamp}.png"
        plt.savefig(os.path.join(ruta_graficos, nombre_grafico_mds), dpi=300)
        plt.close()
        print(f"¡Gráfico de distancias optimizado generado con éxito! Guardado en: Graficos/{nombre_grafico_mds}")

    else:
        print("\nDECISIÓN ESTADÍSTICA:")
        print("p-value >= 0.01. No se rechaza H0. Los perfiles son estadísticamente equivalentes.")

    # ==============================================================================
    # 7. FASE 5: VISUALIZACIÓN ESPACIAL TRIDIMENSIONAL INTERACTIVA (REAL 3D)
    # ==============================================================================
    print("\n" + "=" * 75)
    print(" FASE 5: GENERANDO ESPACIO TRIDIMENSIONAL REAL INTERACTIVO (PLOTLY) ")
    print("=" * 75)
    print("Construyendo cubo de dispersión tridimensional con centroides reales...")
    
    import plotly.graph_objects as go

    df_3d = df_muestra[variables_y].copy()
    df_3d['Cohorte'] = grupos_lista

    paleta_3d = {'Pass': '#66c2a5', 'Distinction': '#fc8d62', 'Fail': '#8da0cb', 'Withdrawn': '#e78ac3'}
    fig = go.Figure()

    # Graficar puntos reales de estudiantes
    for cohorte in df_3d['Cohorte'].unique():
        df_sub_3d = df_3d[df_3d['Cohorte'] == cohorte]
        fig.add_trace(go.Scatter3d(
            x=df_sub_3d['total_clicks_plataforma'],
            y=df_sub_3d['nota_promedio'],
            z=df_sub_3d['porcentaje_entregas_a_tiempo'],
            mode='markers',
            marker=dict(size=4, color=paleta_3d[cohorte], opacity=0.5),
            name=f"Estudiantes: {cohorte}"
        ))

    # Calcular e inyectar centroides tridimensionales
    for cohorte in df_3d['Cohorte'].unique():
        df_sub_3d = df_3d[df_3d['Cohorte'] == cohorte]
        c_x = df_sub_3d['total_clicks_plataforma'].mean()
        c_y = df_sub_3d['nota_promedio'].mean()
        c_z = df_sub_3d['porcentaje_entregas_a_tiempo'].mean()
        
        fig.add_trace(go.Scatter3d(
            x=[c_x], y=[c_y], z=[c_z],
            mode='markers',
            marker=dict(size=12, color=paleta_3d[cohorte], symbol='x', 
                        line=dict(color='black', width=2)),
            name=f"CENTROIDE: {cohorte}"
        ))

    fig.update_layout(
        title="Espacio de Comportamiento Multidimensional Real (OULAD)",
        scene=dict(
            xaxis_title="Y1: Total Clics Plataforma",
            yaxis_title="Y2: Nota Promedio (0-100)",
            zaxis_title="Y3: % Entregas a Tiempo"
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        legend=dict(title_text="Ecosistema Estudiantil")
    )

    ruta_html = os.path.join(ruta_graficos, f"permanova_cubo_3d_{timestamp}.html")
    fig.write_html(ruta_html)
    print(f"Gráfico 3D interactivo guardado en: {ruta_html}")
 

if __name__ == "__main__":
    ejecutar_analisis_multivariante_permanova()