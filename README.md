# 🔍 Analizador de Feedback de Clientes con IA

Sistema inteligente para analizar conversaciones, tickets y sugerencias de clientes, identificando automáticamente oportunidades de mejora y dolores usando IA de Anthropic.

## 🚀 Características Principales

- **📁 Procesamiento Multi-formato**: Lee archivos XLSX, XLS, CSV, DOCX y PDF
- **🧠 Análisis con IA**: Identifica automáticamente hasta 3 oportunidades por input usando Claude
- **🔗 Deduplicación Inteligente**: Fusiona oportunidades similares para evitar repeticiones
- **💾 Base de Conocimientos**: Almacena y gestiona todas las oportunidades identificadas
- **💬 Chat con IA**: Interfaz conversacional para explorar insights
- **🌐 Interfaz Web**: Dashboard interactivo con Streamlit
- **📊 Visualizaciones**: Gráficos y estadísticas de los datos analizados

## 📋 Requisitos

- Python 3.8+
- API Key de Anthropic (Claude)
- Dependencias listadas en `requirements.txt`

## ⚙️ Instalación

1. **Clonar o descargar el proyecto**

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar API Key:**
```bash
# Opción 1: Variable de entorno
export ANTHROPIC_API_KEY="tu_api_key_aqui"

# Opción 2: Archivo .env
cp .env.template .env
# Editar .env con tu API key
```

4. **Verificar instalación:**
```bash
cd src
python main.py stats
```

## 🖥️ Formas de Uso

### 1. Interfaz Web (Recomendado)

```bash
streamlit run streamlit_app.py
```

La interfaz web incluye:
- 📊 **Dashboard**: Estadísticas y visualizaciones
- 📁 **Procesar Archivos**: Subir y analizar archivos
- 🔍 **Buscar**: Explorar oportunidades identificadas
- 💬 **Chat**: Conversación con IA sobre insights
- 📜 **Historial**: Ver archivos procesados

### 2. Línea de Comandos (CLI)

```bash
cd src

# Procesar un archivo individual
python main.py process-file ../datos/conversaciones.xlsx

# Procesar directorio completo
python main.py process-directory ../datos/

# Ver estadísticas
python main.py stats

# Buscar oportunidades
python main.py search "problemas de login"

# Chat interactivo
python main.py chat

# Ver historial
python main.py history
```

### 3. API Programática

```python
from src.main import CustomerFeedbackAnalyzer

# Inicializar
analyzer = CustomerFeedbackAnalyzer(api_key="tu_api_key")

# Procesar archivo
result = analyzer.process_file("ruta/al/archivo.xlsx")

# Obtener estadísticas
stats = analyzer.get_summary()

# Buscar oportunidades
opportunities = analyzer.search_opportunities("login")

# Chat con IA
response = analyzer.chat("¿Cuáles son los principales dolores de clientes?")
```

## 📂 Estructura del Proyecto

```
Analizador de conversaciones/
├── src/                          # Código fuente principal
│   ├── __init__.py
│   ├── main.py                   # Orquestador principal y CLI
│   ├── file_processors.py       # Procesamiento de archivos
│   ├── content_extractor.py     # Extracción de contenido
│   ├── ai_analyzer.py           # Análisis con IA
│   ├── knowledge_base.py        # Base de datos SQLite
│   └── chat_interface.py        # Chat conversacional
├── data/                         # Base de datos (auto-generada)
│   └── customer_insights.db
├── streamlit_app.py             # Interfaz web
├── requirements.txt             # Dependencias
├── .env.template               # Plantilla de configuración
├── README.md                   # Este archivo
└── conversaciones_log.md       # Log de conversaciones
```

## 🔧 Configuración

### Variables de Entorno

- `ANTHROPIC_API_KEY`: API Key de Anthropic (requerido)
- `AI_MODEL`: Modelo de IA (default: claude-3-haiku-20240307)
- `DB_PATH`: Ruta de la base de datos (default: data/customer_insights.db)
- `SIMILARITY_THRESHOLD`: Umbral de similitud para fusión (default: 0.8)
- `MAX_OPPORTUNITIES_PER_INPUT`: Máximo oportunidades por input (default: 3)

### Personalización

El sistema identifica automáticamente:
- **Identificadores**: IDs de tickets, conversaciones, nombres de cliente
- **Tipos de contenido**: Conversaciones, tickets, sugerencias
- **Categorías**: pain_point, improvement_opportunity, feature_request
- **Severidades**: low, medium, high, critical

## 📊 Tipos de Análisis

### 1. Identificación de Estructura
- Detecta automáticamente la estructura de los datos
- Identifica columnas de ID y contenido
- Adapta el parser según el formato

### 2. Extracción de Contenido
- Parsea conversaciones individuales
- Extrae tickets con metadata
- Procesa sugerencias de clientes

### 3. Análisis con IA
- Identifica hasta 3 oportunidades por input
- Clasifica por categoría y severidad
- Extrae palabras clave relevantes

### 4. Deduplicación
- Usa embeddings semánticos para detectar similitudes
- Fusiona oportunidades duplicadas
- Mantiene trazabilidad de fuentes

## 🎯 Ejemplos de Uso

### Procesar Conversaciones de Soporte
```bash
# Si tienes un Excel con conversaciones de chat
python main.py process-file conversaciones_soporte.xlsx

# También soporta CSV y XLS
python main.py process-file feedback_clientes.csv
python main.py process-file tickets_antiguos.xls

# El sistema identificará automáticamente:
# - IDs de conversación/ticket
# - Contenido del chat/feedback
# - Problemas mencionados
# - Oportunidades de mejora
```

### Analizar Tickets de Helpdesk
```bash
# Procesar tickets en formato DOCX
python main.py process-file tickets_enero.docx

# Identificará:
# - Números de ticket
# - Categorías de problemas
# - Solicitudes de funcionalidades
# - Dolores frecuentes
```

### Explorar con Chat
```bash
python main.py chat
# > ¿Cuáles son los principales problemas de login?
# > ¿Qué funcionalidades han pedido más los clientes?
# > Muéstrame las oportunidades críticas
```

## 🤖 Prompts de IA

El sistema usa prompts especializados que:
- Analizan en español
- Identifican máximo 3 oportunidades por input
- Clasifican por categoría y severidad
- Solo reportan oportunidades reales (no inventadas)
- Extraen keywords relevantes

## 📈 Dashboard y Reportes

La interfaz web proporciona:
- **Métricas clave**: Total elementos, oportunidades, archivos
- **Distribuciones**: Por categoría, severidad, frecuencia
- **Top keywords**: Palabras más mencionadas
- **Tendencias**: Evolución temporal de oportunidades
- **Búsqueda avanzada**: Filtros por múltiples criterios

## 🔍 Búsqueda y Filtros

- **Búsqueda textual**: En títulos, descripciones y keywords
- **Filtros por categoría**: pain_point, improvement_opportunity, feature_request
- **Filtros por severidad**: low, medium, high, critical
- **Filtro por frecuencia**: Oportunidades mencionadas múltiples veces
- **Ordenamiento**: Por relevancia, frecuencia, severidad

## 💾 Base de Datos

Almacena en SQLite:
- **content_items**: Elementos originales procesados
- **opportunities**: Oportunidades identificadas y deduplicadas
- **file_processing_log**: Historial de archivos procesados
- **insights_cache**: Cache de respuestas de chat

## 🚨 Manejo de Errores

- Logs detallados de procesamiento
- Continuación en caso de errores de archivos individuales
- Validación de formatos de entrada
- Manejo de límites de API
- Respaldos automáticos de datos

## 🔒 Consideraciones de Seguridad

- API Keys manejadas como variables de entorno
- No se almacenan datos sensibles en logs
- Base de datos local (no cloud por default)
- Validación de tipos de archivo

## 🆘 Solución de Problemas

### Error de API Key
```bash
export ANTHROPIC_API_KEY="tu_api_key"
# o editar .env
```

### Errores de Dependencias
```bash
pip install -r requirements.txt --force-reinstall
```

### Base de Datos Corrupta
```bash
rm data/customer_insights.db
# Se recreará automáticamente
```

### Archivos No Reconocidos
- Verificar formato (xlsx, docx, pdf)
- Comprobar que el archivo no esté corrupto
- Revisar permisos de lectura

## 📝 Próximas Mejoras

- [ ] Soporte para más formatos (CSV, TXT, JSON)
- [ ] Integración con APIs de CRM
- [ ] Análisis de sentimiento
- [ ] Clasificación automática de clientes
- [ ] Alertas automáticas para oportunidades críticas
- [ ] Exportación de reportes (PDF, PowerPoint)
- [ ] Integración con Slack/Teams

## 🤝 Contribución

Para contribuir al proyecto:
1. Fork el repositorio
2. Crear branch para feature
3. Implementar cambios
4. Agregar tests si es necesario
5. Crear pull request

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver archivo LICENSE para más detalles.

---

**Desarrollado con ❤️ para mejorar la experiencia del cliente mediante IA**