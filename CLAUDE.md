# Analizador de Conversaciones IA - Configuración y Memoria del Proyecto

## Sistema de Memoria Persistente

### Configuración Actual
Este proyecto está configurado con un **sistema de memoria persistente** que permite mantener continuidad entre sesiones de Claude Code.

#### Archivos de Memoria
- **conversaciones_log.md**: Registro detallado de todas las conversaciones y decisiones
- **estado_proyecto.json**: Estado técnico del proyecto en formato JSON
- **CLAUDE.md**: Documentación e instrucciones del proyecto (este archivo)

### Instrucciones para Claude

#### Al Iniciar Cada Sesión
1. **Leer siempre** los archivos de memoria al comenzar:
   - `conversaciones_log.md` para contexto de sesiones anteriores
   - `estado_proyecto.json` para estado técnico actual
   - Este archivo `CLAUDE.md` para instrucciones específicas

2. **Actualizar** estos archivos al final de cada sesión con:
   - Nuevas conversaciones y decisiones tomadas
   - Cambios en el estado del proyecto
   - Archivos creados o modificados
   - Próximos pasos identificados

#### Protocolo de Trabajo
- **SIEMPRE** usar la herramienta TodoWrite para tareas complejas
- **ACTUALIZAR** estado_proyecto.json después de cambios significativos
- **REGISTRAR** todas las conversaciones importantes en conversaciones_log.md
- **MANTENER** continuidad entre sesiones consultando archivos de memoria

### Estructura del Proyecto

#### Archivos de Datos
- Archivos CSV con conversaciones de IA
- Documentos PDF de estrategia empresarial
- Documentos DOCX de procesos

#### Archivos de Análisis
- Resultados de análisis previos
- Reportes generados
- Visualizaciones creadas

#### Sistema de Memoria
- conversaciones_log.md
- estado_proyecto.json
- CLAUDE.md (este archivo)

### Objetivos del Proyecto
- Analizar conversaciones de IA relacionadas con vacaciones y ausencias
- Identificar temas estratégicos para mejora de experiencia de usuario
- Mantener continuidad entre sesiones de trabajo
- Iterar y mejorar el producto basado en análisis continuos

### Herramientas Recomendadas
- **Archivos grandes**: Usar herramientas bash (grep, cut, sort, uniq)
- **PDFs**: Convertir con pdftotext o Python
- **DOCX**: Convertir con pandoc o Python
- **CSV**: Procesar por partes si es necesario

---

**IMPORTANTE**: Este proyecto requiere memoria persistente. Siempre consultar y actualizar los archivos de memoria para mantener continuidad entre sesiones.

*Configurado: 17 de septiembre, 2025*