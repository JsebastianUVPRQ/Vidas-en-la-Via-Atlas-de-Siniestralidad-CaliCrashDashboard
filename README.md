# CaliCrashDashboard - Pronóstico de Siniestralidad Vial en Cali

Dashboard interactivo en Streamlit que modela la frecuencia de accidentes de tránsito en Cali, basado en datos abiertos de la Secretaría de Movilidad. La aplicación muestra un mapa con las zonas de mayor concentración de siniestros, permitiendo filtrar por comuna, intersección y franja horaria.

## 📊 Fuente de datos
- [Datos Abiertos de la Alcaldía de Cali – Secretaría de Movilidad]
- Archivos CSV/JSON con registros históricos de accidentes (georreferenciados).

## 🛠 Tecnologías
- **Python 3.10+**
- **Streamlit** (frontend/dashboard)
- **Pandas, GeoPandas** (manejo de datos)
- **Folium / PyDeck / Plotly** (visualización geoespacial interactiva)
- **Statsmodels / Scikit-learn** (modelado de frecuencias)
- **Streamlit Cloud** (despliegue sin servidor propio)


## ☁️ Despliegue en Streamlit Cloud
- Conecta tu repositorio de GitHub a [Streamlit Cloud](https://share.streamlit.io).
- Selecciona el archivo principal `app.py`.
- Listo, la app se actualizará con cada push.

## 📁 Estructura del proyecto
```
.
├── app.py               # Punto de entrada de la aplicación
├── src/                 # Código fuente de procesamiento, modelado y visualización
├── data/                # Datos crudos y procesados (gitignorados si son grandes)
├── notebooks/           # Análisis exploratorio y prototipos
├── requirements.txt
├── AGENTS.md            # Instrucciones para agentes de IA
└── SPECS.md             # Especificaciones técnicas
```

## 📌 Estado del proyecto
En desarrollo activo. Próximas funcionalidades: predicción de siniestros por día/hora, alertas automáticas.
