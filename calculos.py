import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import io
import networkx as nx

# Lista de feriados
FERIADOS = {datetime.strptime(date, "%Y-%m-%d").date() for date in [
    "2025-01-01", "2025-04-18", "2025-05-01", "2025-07-28", "2025-07-29", "2025-12-25"
]}

def obtener_fechas_laborales(fecha_inicio, num_dias):
    """Genera una lista de fechas laborales excluyendo sábados, domingos y feriados."""
    fechas = []
    fecha_actual = fecha_inicio.date()

    while len(fechas) < num_dias:
        if fecha_actual.weekday() < 5 and fecha_actual not in FERIADOS:
            fechas.append(datetime.combine(fecha_actual, datetime.min.time()))
        fecha_actual += timedelta(days=1)

    return fechas

def calcular_tiempos_inicio(df_actividades, orden_topologico, matriz_adyacencia):
    """Calcula los tiempos de inicio considerando dependencias."""
    tiempos_inicio = np.zeros(len(df_actividades))

    for idx in orden_topologico:
        predecesores = np.where(matriz_adyacencia[:, idx] == 1)[0]
        max_inicio = 0

        for predecesor in predecesores:
            duracion_predecesor = df_actividades.loc[predecesor, 'Duración']
            if pd.notna(duracion_predecesor) and duracion_predecesor > 0:
                inicio_predecesor = tiempos_inicio[predecesor]
                max_inicio = max(max_inicio, inicio_predecesor + duracion_predecesor)

        tiempos_inicio[idx] = max_inicio

    return tiempos_inicio

def generar_matriz_contractual(df_actividades, tiempos_inicio, duracion_total):
    """Genera la matriz contractual C basada en tiempos de inicio y duración."""
    num_actividades = len(df_actividades)
    C = np.zeros((num_actividades, duracion_total))

    for idx, row in df_actividades.iterrows():
        duracion = int(row['Duración']) if pd.notna(row['Duración']) else 0
        unidades = float(row['Unidades a Producir']) if pd.notna(row['Unidades a Producir']) else 0
        inicio = int(tiempos_inicio[idx])

        if duracion > 0 and unidades > 0:
            produccion_diaria = unidades / duracion
            fin = min(inicio + duracion, duracion_total)
            C[idx, inicio:fin] = produccion_diaria

    return C

def generar_matriz_restricciones(df_actividades, restricciones, fecha_inicio_proyecto, duracion_total):
    """Genera la matriz de restricciones R con base en las restricciones definidas."""
    num_actividades = len(df_actividades)
    R = np.ones((num_actividades, duracion_total))  

    for _, restr in restricciones.iterrows():
        nombre_act = restr['Nombre de Actividad']
        if nombre_act not in df_actividades['Nombre de Actividad'].values:
            continue  

        idx = df_actividades[df_actividades['Nombre de Actividad'] == nombre_act].index[0]
        fecha_inicio = restr['Fecha de Inicio']
        fecha_fin = restr['Fecha de Fin']
        porcentaje = restr['%Parcial']

        dias_restringidos = pd.date_range(start=fecha_inicio, end=fecha_fin)

        for dia in dias_restringidos:
            dia_idx = (dia - fecha_inicio_proyecto).days
            if 0 <= dia_idx < duracion_total:
                R[idx, dia_idx] = porcentaje  

    return R

import numpy as np

import numpy as np

def generar_matriz_contractual_ajustada(df_actividades, matriz_C, matriz_R, matriz_adyacencia, tiempos_inicio_ajustados, duracion_total):
    """
    Ajusta la matriz contractual C según las restricciones R y las dependencias entre actividades.
    - Se garantiza que las actividades inicien cuando sus predecesoras terminan.
    - Se ajusta la producción diaria con base en restricciones parciales sin retrasar innecesariamente la actividad.
    - Se extiende el tiempo total de duración si es necesario.
    """
    num_actividades, _ = matriz_C.shape
    max_duracion = duracion_total * 2  # Se amplía la duración temporalmente para asegurar suficiente espacio
    C_ajustada = np.zeros((num_actividades, max_duracion))  # Inicializar con ceros

    for i in range(num_actividades):
        # Obtener producción original y su rango de tiempo en C
        produccion_original = matriz_C[i, :]
        indices_no_cero = np.where(produccion_original > 0)[0]

        if len(indices_no_cero) == 0:
            continue  # No hay producción para esta actividad

        inicio_original = indices_no_cero[0]
        produccion_diaria = produccion_original[inicio_original]
        unidades_totales = sum(produccion_original)  # Producción total que debe cumplirse

        # Determinar el tiempo de inicio ajustado según dependencias
        predecesores = np.where(matriz_adyacencia[:, i] == 1)[0]
        inicio_ajustado = int(tiempos_inicio_ajustados[i])  # Asegurar entero

        if len(predecesores) > 0:
            fin_predecesores = [int(tiempos_inicio_ajustados[p]) + int(df_actividades.loc[p, 'Duración']) for p in predecesores]
            inicio_ajustado = max(inicio_ajustado, max(fin_predecesores))  # Esperar a que todas las predecesoras terminen

        # **🔹 Corregimos la aplicación de restricciones parciales**
        while inicio_ajustado < duracion_total and matriz_R[i, inicio_ajustado] == 0:
            inicio_ajustado += 1  # Solo retrasamos si la restricción es total (0)

        # **🔹 Aplicamos restricciones en la producción sin retrasar innecesariamente**
        dia_actual = inicio_ajustado
        acumulado = 0  # Seguimiento de producción acumulada
        unidades_faltantes = unidades_totales  # Producción que aún falta completar

        while acumulado < unidades_totales and dia_actual < C_ajustada.shape[1]:
            if dia_actual >= matriz_R.shape[1]:  # Evitar índices fuera de rango
                break

            restriccion = matriz_R[i, dia_actual]  # Factor de restricción del día actual

            # Si la restricción es total (0), no se produce y se avanza al siguiente día
            if restriccion == 0:
                dia_actual += 1
                continue

            # Aplicar restricción parcial: afecta producción diaria sin retrasar el inicio
            nueva_produccion = produccion_diaria * restriccion
            C_ajustada[i, dia_actual] = nueva_produccion
            acumulado += nueva_produccion
            unidades_faltantes -= nueva_produccion

            # Pasar al siguiente día
            dia_actual += 1

        # **🔹 Si no se ha producido toda la cantidad requerida, continuar produciendo respetando restricciones**
        while acumulado < unidades_totales and dia_actual < max_duracion:
            restriccion = matriz_R[i, dia_actual] if dia_actual < matriz_R.shape[1] else 1.0  # Considerar restricción del día
            
            if restriccion > 0:  # Si no es una restricción total, puede seguir produciendo
                nueva_produccion = produccion_diaria * restriccion
                nueva_produccion = min(nueva_produccion, unidades_faltantes)  # No sobreproducir
                C_ajustada[i, dia_actual] = nueva_produccion
                acumulado += nueva_produccion
                unidades_faltantes -= nueva_produccion

            dia_actual += 1

    # **🔹 Determinar el tamaño real de la matriz sin columnas vacías innecesarias**
    if np.any(C_ajustada):  # Verificar que haya valores
        duracion_final = max(np.where(C_ajustada.any(axis=0))[0]) + 1
    else:
        duracion_final = duracion_total

    C_ajustada = C_ajustada[:, :duracion_final]  # Recortar a la dimensión real

    return C_ajustada.tolist()



def calcular_tiempos_inicio_ajustados(df_actividades, orden_topologico, matriz_adyacencia, matriz_R, fecha_inicio_proyecto, duracion_total):
    """Calcula los tiempos de inicio ajustados \( T_i' \) considerando restricciones y dependencias."""
    
    tiempos_inicio = np.zeros(len(df_actividades))

    for idx in orden_topologico:
        predecesores = np.where(matriz_adyacencia[:, idx] == 1)[0]
        max_inicio = 0  # El mayor tiempo de inicio considerando dependencias

        # **🔹 Revisamos cada predecesor**
        for predecesor in predecesores:
            if predecesor < len(df_actividades):
                duracion_predecesor = df_actividades.loc[predecesor, 'Duración']
                if pd.notna(duracion_predecesor) and duracion_predecesor > 0:
                    inicio_predecesor = tiempos_inicio[predecesor]
                    max_inicio = max(max_inicio, inicio_predecesor + duracion_predecesor)

        # **🔹 Aplicar restricciones (solo si son totales, es decir, 0)**
        dia_inicio = fecha_inicio_proyecto + timedelta(days=int(max_inicio))

        # **🔹 Corregimos para que solo las restricciones totales retrasen la actividad**
        while 0 <= (dia_inicio - fecha_inicio_proyecto).days < duracion_total and matriz_R[idx, int((dia_inicio - fecha_inicio_proyecto).days)] == 0:
            dia_inicio += timedelta(days=1)
            max_inicio += 1  # Se retrasa solo si la restricción es 0 (total)

        tiempos_inicio[idx] = max_inicio  # Guardamos el inicio ajustado

    return tiempos_inicio

def generar_matriz_adyacencia_ajustada(df_actividades, tiempos_inicio_ajustados):
    """Genera la matriz de adyacencia ajustada \( A' \) después de considerar restricciones."""
    
    num_actividades = len(df_actividades)
    A_ajustada = np.zeros((num_actividades, num_actividades))

    for idx, row in df_actividades.iterrows():
        predecesoras = str(row['Predecesoras']).split(',')
        for pred in predecesoras:
            pred = pred.strip()
            if pred.isdigit():
                pred_idx = int(pred)
                if pred_idx < len(tiempos_inicio_ajustados) and idx < len(tiempos_inicio_ajustados):
                    if tiempos_inicio_ajustados[pred_idx] < tiempos_inicio_ajustados[idx]:
                        A_ajustada[pred_idx, idx] = 1  

    return A_ajustada

def calcular_ruta_critica_ajustada(A_ajustada, df_actividades, tiempos_inicio_ajustados):
    """Calcula la nueva ruta crítica basada en la matriz de adyacencia ajustada y tiempos de inicio ajustados."""

    if not np.any(A_ajustada):
        print("⚠️ Error: La matriz de adyacencia ajustada está vacía. No se puede calcular la ruta crítica.")
        return None, None

    G = nx.DiGraph(A_ajustada)

    if len(G.nodes) == 0:
        print("⚠️ Error: El grafo de la ruta crítica ajustada no tiene nodos.")
        return None, None

    try:
        ruta_critica = nx.dag_longest_path(G, weight='weight')

        if not ruta_critica:
            print("⚠️ Error: No se pudo calcular la ruta crítica ajustada.")
            return None, None

        duracion_total_ajustada = sum(
            int(df_actividades.loc[act, 'Duración']) for act in ruta_critica
            if pd.notna(df_actividades.loc[act, 'Duración'])
        )

        return ruta_critica, duracion_total_ajustada

    except Exception as e:
        print(f"⚠️ Error en el cálculo de la ruta crítica ajustada: {str(e)}")
        return None, None

def convertir_a_excel(df_C, df_C_ajustada, df_R, df_actividades, fecha_inicio_proyecto):
    """Convierte matrices en un archivo Excel con fechas laborales y días de la semana."""
    fechas = obtener_fechas_laborales(fecha_inicio_proyecto, len(df_C.columns))
    etiquetas_fechas = [fecha.strftime("%Y-%m-%d") for fecha in fechas]
    
    df_C.insert(0, "Actividad", df_actividades["Nombre de Actividad"])
    df_C_ajustada.insert(0, "Actividad", df_actividades["Nombre de Actividad"])
    df_R.insert(0, "Actividad", df_actividades["Nombre de Actividad"])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_C.to_excel(writer, sheet_name="Matriz C", index=False)
        df_C_ajustada.to_excel(writer, sheet_name="Matriz C Ajustada", index=False)
        df_R.to_excel(writer, sheet_name="Matriz R", index=False)
    
    return output.getvalue()


