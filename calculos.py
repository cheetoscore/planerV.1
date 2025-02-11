import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import io

from datetime import datetime

# Lista de feriados (convertidos a datetime automáticamente)
FERIADOS = {datetime.strptime(date, "%Y-%m-%d").date() for date in [
    "2025-01-01", "2025-04-18", "2025-05-01", "2025-07-28", "2025-07-29", "2025-12-25"
]}

def obtener_fechas_laborales(fecha_inicio, num_dias):
    """Genera una lista de fechas laborales excluyendo sábados, domingos y feriados."""
    fechas = []
    fecha_actual = fecha_inicio.date()  # Convertir a date para evitar errores de tipo

    while len(fechas) < num_dias:
        if fecha_actual.weekday() < 5 and fecha_actual not in FERIADOS:
            fechas.append(datetime.combine(fecha_actual, datetime.min.time()))  # Convertir de nuevo a datetime
        fecha_actual += timedelta(days=1)

    return fechas

def calcular_tiempos_inicio(df_actividades, orden_topologico, matriz_adyacencia):
    """Calcula los tiempos de inicio de las actividades considerando dependencias y avances parciales."""
    
    tiempos_inicio = np.zeros(len(orden_topologico))  # Usa NumPy para mejor rendimiento
    
    
    
    for idx in orden_topologico:
        predecesores = np.where(matriz_adyacencia[:, idx] == 1)[0]
        avances = str(df_actividades.loc[idx, 'Avance Necesario']).split(',')
        avances = [float(a.strip()) if a.strip() else 1.0 for a in avances]  # Limpia y convierte avances
        max_inicio = 0

        for i, predecesor in enumerate(predecesores):
            if i >= len(avances):  # Evita errores de índice si hay menos avances que predecesores
                avance_parcial = 1.0
            else:
                avance_parcial = avances[i]
            
            duracion_predecesor = df_actividades.loc[predecesor, 'Duración']
            if pd.notna(duracion_predecesor) and duracion_predecesor > 0:  # Evita valores NaN o negativos
                inicio_predecesor = tiempos_inicio[predecesor]
                max_inicio = max(max_inicio, inicio_predecesor + avance_parcial * duracion_predecesor)

        tiempos_inicio[idx] = max_inicio  # Asigna el mayor tiempo calculado

    return tiempos_inicio


def generar_matriz_contractual(df_actividades, tiempos_inicio, duracion_total):
    """Genera la matriz contractual basada en los tiempos de inicio y duración de las actividades."""
    
    num_actividades = len(df_actividades)
    C = np.zeros((num_actividades, duracion_total))

    for idx, row in df_actividades.iterrows():
        duracion = int(row['Duración']) if pd.notna(row['Duración']) else 0
        unidades = float(row['Unidades a Producir']) if pd.notna(row['Unidades a Producir']) else 0
        inicio = int(tiempos_inicio[idx])

        if duracion > 0 and unidades > 0:
            produccion_diaria = unidades / duracion
            fin = min(inicio + duracion, duracion_total)  # Evita desbordamiento de matriz
            C[idx, inicio:fin] = produccion_diaria

    return C

def convertir_a_excel(df, df_actividades, fecha_inicio_proyecto):
    """Convierte la matriz contractual en un archivo Excel con fechas laborales y días de la semana."""
    
    # Convertir fecha de inicio a datetime si es necesario
    if isinstance(fecha_inicio_proyecto, datetime):
        fecha_inicio = fecha_inicio_proyecto
    else:
        fecha_inicio = datetime.combine(fecha_inicio_proyecto, datetime.min.time())

    # Obtener solo días laborales
    fechas = obtener_fechas_laborales(fecha_inicio, len(df.columns))

    # Convertir fechas a string (YYYY-MM-DD) y obtener días de la semana
    etiquetas_fechas = [fecha.strftime("%Y-%m-%d") for fecha in fechas]
    etiquetas_dias = [fecha.strftime("%a").capitalize() for fecha in fechas]  # Lun, Mar, Mié...

    # Agregar nombres de actividades como primera columna
    df.insert(0, "Actividad", df_actividades["Nombre de Actividad"])

    # Crear un DataFrame con la fila adicional para los días de la semana
    df_dias = pd.DataFrame([["Día de la semana"] + etiquetas_dias], columns=df.columns)
    
    # Concatenar la fila de días con la matriz original
    df_final = pd.concat([df_dias, df], ignore_index=True)

    # Asignar etiquetas de columnas con fechas laborales
    df_final.columns = ["Actividad"] + etiquetas_fechas

    # Convertir a Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_final.to_excel(writer, sheet_name="Matriz Contractual", index=False)
    processed_data = output.getvalue()

    return processed_data

###################################################################################################
def generar_matriz_contractual_ajustada(df_actividades, matriz_C, matriz_R, matriz_adyacencia, tiempos_inicio_ajustados, duracion_total):
    """
    Ajusta la matriz contractual C según las restricciones R y las dependencias entre actividades.
    - Se garantiza que las actividades inicien cuando sus predecesoras terminan.
    - Se ajusta la producción diaria con base en restricciones parciales sin retrasar innecesariamente la actividad.
    - Se extiende el tiempo total de duración si es necesario.
    """
    num_actividades, _ = matriz_C.shape
    max_duracion = duracion_total * 2  # Se amplía la duración temporalmente
    C_ajustada = np.zeros((num_actividades, max_duracion))  # Matriz expandida para posibles retrasos

    for i in range(num_actividades):
        # Obtener producción original y rango de tiempo en C
        produccion_original = matriz_C[i, :]
        indices_no_cero = np.where(produccion_original > 0)[0]

        if len(indices_no_cero) == 0:
            continue  # No hay producción para esta actividad

        inicio_original = indices_no_cero[0]
        produccion_diaria = produccion_original[inicio_original]
        unidades_totales = sum(produccion_original)

        # Determinar el tiempo de inicio considerando predecesoras
        predecesores = np.where(matriz_adyacencia[:, i] == 1)[0]
        inicio_ajustado = int(tiempos_inicio_ajustados[i])  # Asegurar que sea entero

        if len(predecesores) > 0:
            fin_predecesores = [int(tiempos_inicio_ajustados[p]) + int(df_actividades.loc[p, 'Duración']) for p in predecesores]
            inicio_ajustado = max(inicio_ajustado, max(fin_predecesores))  # Espera a que todas terminen

        # Ajustar producción en C' según restricciones en R
        dia_actual = inicio_ajustado
        acumulado = 0  # Seguimiento de producción acumulada

        while acumulado < unidades_totales and dia_actual < max_duracion:
            # Evitar índices fuera de rango
            if dia_actual >= matriz_R.shape[1]:  
                break

            # Verificar restricción y evitar errores
            restriccion = matriz_R[i, dia_actual] if not np.isnan(matriz_R[i, dia_actual]) else 1.0  # Si es NaN, asumir sin restricción

            # Si la restricción es total (0), no se produce y se avanza al siguiente día
            if restriccion == 0:
                dia_actual += 1
                continue

            # Si la restricción es parcial (<1 pero >0), la actividad inicia con producción reducida
            nueva_produccion = produccion_diaria * restriccion
            C_ajustada[i, dia_actual] = nueva_produccion
            acumulado += nueva_produccion

            # Pasar al siguiente día
            dia_actual += 1

        # Si no se ha producido toda la cantidad requerida, continuar en los siguientes días
        while acumulado < unidades_totales and dia_actual < max_duracion:
            C_ajustada[i, dia_actual] = produccion_diaria
            acumulado += produccion_diaria
            dia_actual += 1

    # Determinar el tamaño real de la matriz sin columnas vacías innecesarias
    if np.any(C_ajustada):  # Verificar que haya valores
        duracion_final = max(np.where(C_ajustada.any(axis=0))[0]) + 1
    else:
        duracion_final = duracion_total

    C_ajustada = C_ajustada[:, :duracion_final]  # Recortar a la dimensión real

    return C_ajustada.tolist()
