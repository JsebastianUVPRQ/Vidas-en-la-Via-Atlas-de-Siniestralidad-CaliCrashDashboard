# Especificaciones técnicas – Pronóstico de Siniestralidad Vial en Cali

## 1. Objetivo
Desarrollar un dashboard Streamlit que:
- Cargue datos abiertos de accidentes de tránsito en Cali.
- Procese, limpie y georreferencie los incidentes.
- Modele la frecuencia de accidentes por zona (comuna / intersección) y franja horaria.
- Muestre un mapa interactivo con la densidad de siniestros y filtros dinámicos.

## 2. Fuente y formato de datos
- **Origen:** Portal de datos abiertos (JSON/CSV) de la Secretaría de Movilidad de Cali.
- **Campos esperados:** fecha, hora, latitud, longitud, comuna, barrio, tipo de accidente, gravedad, intersección (opcional).
- **Frecuencia de actualización:** mensual (se descargará un snapshot acumulado, o se usará API si está disponible).

## 3. Arquitectura de software
```mermaid
graph TD
    A[Datos abiertos] --> B[ETL: limpieza, imputación, geocodificación]
    B --> C[Base procesada en Parquet/CSV]
    C --> D[Modelado estadístico (Poisson, NB, SARIMA?)]
    D --> E[Resultados: frecuencias esperadas por zona/hora]
    E --> F[Dashboard Streamlit]
    F --> G[Mapa interactivo + filtros]
    G --> H[Visualización en Streamlit Cloud]
```

- **Librerías clave:** pandas, geopandas, folium, streamlit-folium, plotly, statsmodels/scikit-learn.
- **Modelado:** análisis de series temporales por zona (frecuencia diaria/horaria) o modelo de regresión para identificar factores de riesgo. El dashboard mostrará valores observados y, opcionalmente, predicciones.

## 4. Funcionalidades del dashboard
1. **Mapa de calor/ clusters** con accidentes agregados por comuna o intersección.
2. **Selectores de fecha/hora** y día de la semana (franjas: madrugada, mañana, tarde, noche).
3. **Gráficos de barras** comparando siniestros por comuna en el período seleccionado.
4. **Indicadores clave:** total de accidentes, promedio diario, comuna más peligrosa.
5. **Opciones de descarga** de datos filtrados.

## 5. Procesamiento de datos
- Conversión de coordenadas si es necesario (EPSG:4326 → proyección local).
- Unión con shapefiles de comunas (disponibles en SIG de Cali).
- Agregación temporal: generar columnas `franja_horaria`, `dia_semana`, `mes`.

## 6. Modelo de frecuencia
- Agregación de conteos por comuna y franja horaria.
- Ajuste de modelos de series de tiempo (por ejemplo, Prophet o SARIMA) para cada comuna, o un modelo global con variables dummy. El dashboard prioriza la visualización de datos históricos; la predicción es un plus.

## 7. Despliegue
- **Streamlit Cloud:** conecta directamente con GitHub. El `requirements.txt` debe incluir todas las dependencias. No se necesita servidor propio.
- **Secreto de API:** si los datos se consumen desde una API, se manejará con `st.secrets`.

## 8. Limitaciones
- Los datos abiertos pueden tener retrasos o campos incompletos.
- La georreferenciación por intersección requiere un diccionario de nombres de calles.
- No se construye aplicación móvil ni backend adicional; todo corre en Streamlit.

## 9. Próximos pasos
- Incorporar notificaciones o reportes automáticos.
- Integrar datos meteorológicos para mejorar la predicción.