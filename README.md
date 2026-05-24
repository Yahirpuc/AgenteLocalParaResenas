import os

# Contenido del README adaptado con la estructura solicitada
readme_content = """# Agente Local de Analítica de Reseñas (RAG Engine)

Sistema profesional de gestión y procesamiento del lenguaje natural para el análisis de activos de información (opiniones de usuarios). Este agente opera bajo un entorno **100% local, privado y de costo cero**, eliminando dependencias de APIs externas o servicios en la nube para garantizar la máxima seguridad de los datos.

---

## 🏗️ Arquitectura del Pipeline

El sistema se compone de cuatro fases desacopladas que procesan la información de manera secuencial:

1. **`extractor.py`**: Raspa y extrae los datos crudos desde las plataformas de origen evadiendo bloqueos mediante la persistencia de sesiones.
2. **`clasificador.py`**: Procesa las opiniones en lotes utilizando el modelo local `qwen2.5:1.5b` estructurando un esquema JSON enriquecido con metadatos de sentimiento y categorías analíticas.
3. **`indexador.py`**: Formatea el contexto de forma aislada mediante bloques de identificación estrictos (`AUTOR:`, `TEXTO DE LA OPINIÓN:`), genera los embeddings vectoriales con `nomic-embed-text` y monta la base de datos persistente en disco utilizando ChromaDB limpiando duplicados obsoletos de ejecuciones previas de forma automática.
4. **`asistente.py`**: Interfaz de consola que implementa un motor de recuperación híbrida (Vectores + BM25 Lexical) y enrutamiento semántico por comandos.

---

## 🛠️ Requisitos del Sistema y Dependencias

Para la correcta ejecución del agente, la máquina local debe contar con soporte para virtualización de entornos y los siguientes modelos desplegados en **Ollama**:

* `qwen2.5:1.5b` (Motor de inferencia y estructuración JSON nativa)
* `nomic-embed-text` (Generador de vectores de características semánticas)

### Dependencias de Python (`requirements.txt`)
