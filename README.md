¡Listo! He vuelto a generar el archivo `README.md` completo en la raíz del entorno para que lo puedas descargar directamente desde aquí, sin que falte ningún componente técnico.

Aquí tienes el archivo listo para descarga:
[file-tag: code-generated-file-0-1779599558803139509]

Y aquí abajo tienes exactamente el bloque de código consolidado, por si necesitas hacer un copiado rápido desde la consola:

```markdown
# Agente Local de Analítica de Reseñas (RAG Engine)

Sistema profesional de gestión y procesamiento del lenguaje natural para el análisis de activos de información (opiniones de usuarios). Este agente opera bajo un entorno **100% local, privado y de costo cero**, eliminando dependencias de APIs externas o servicios en la nube para garantizar la máxima seguridad y confidencialidad de los datos.

---

## 🏗️ 1. Arquitectura y Flujo de Datos

El pipeline está completamente desacoplado en cuatro fases secuenciales para garantizar la escalabilidad y una gestión eficiente de la memoria RAM en la máquina local:


```

[extractor.py]               # Ejecuta Playwright y gestiona la sesión visual interactiva
│
▼ (reseñas_crudas.json)
[clasificador.py]            # Inferencia en lotes con Qwen2.5 (JSON nativo estructurado)
│
▼ (reseñas_enriquecidas.json)
[indexador.py]               # Formateo estricto de nodos e inyección en ChromaDB
│
▼ (Persistencia en disco: /chroma_db)
[asistente.py]               # Motor RAG híbrido (Vectores + BM25 Lexical) con comandos

```

1. **`extractor.py`**: Raspa y extrae los datos crudos desde las plataformas de origen evadiendo bloqueos mediante la persistencia de sesiones utilizando Playwright.
2. **`clasificador.py`**: Procesa las opiniones en lotes utilizando el modelo local `qwen2.5:1.5b` estructurando un esquema JSON enriquecido con metadatos de sentimiento y categorías analíticas de grano fino.
3. **`indexador.py`**: Formatea el contexto de forma aislada mediante bloques de identificación estrictos (`AUTOR:`, `TEXTO DE LA OPINIÓN:`), genera los embeddings vectoriales con `nomic-embed-text` y monta la base de datos persistente en disco utilizando ChromaDB, limpiando registros obsoletos de forma automática.
4. **`asistente.py`**: Interfaz de consola que implementa un motor de recuperación híbrida (Vectores + BM25 Lexical) y enrutamiento semántico por comandos diagonales.

---

## 🛠️ 2. Requisitos del Sistema y Entorno Local

### A. Dependencia Obligatoria: Ollama
Este proyecto ejecuta modelos de lenguaje avanzados de forma local. Es **estrictamente necesario** tener instalado [Ollama](https://ollama.com/) en el sistema operativo y mantener el servicio activo en segundo plano antes de iniciar cualquier script de Python.

Desde la consola de tu sistema operativo, descarga los dos modelos obligatorios del ecosistema:
```bash
# Descargar el motor de inferencia, análisis de sentimiento y clasificación categórica
ollama pull qwen2.5:1.5b

# Descargar el generador de vectores de características semánticas
ollama pull nomic-embed-text

```

### B. Dependencias de Python (`requirements.txt`)

Crea un archivo de texto con el nombre `requirements.txt` e instala las siguientes librerías de producción:

```text
chromadb>=0.4.0
llama-index-core
llama-index-vector-stores-chroma
llama-index-embeddings-ollama
llama-index-llms-ollama
playwright

```

---

## 🚀 3. Guía de Instalación y Despliegue Paso a Paso

Sigue esta secuencia de comandos en tu terminal para construir el entorno virtual aislado:

```bash
# 1. Crear el entorno virtual de Python
python -m venv venv

# 2. Activar el entorno (En Windows / PowerShell)
.\venv\Scripts\Activate.ps1

# 3. Instalar las librerías del proyecto
pip install -r requirements.txt

# 4. Instalar los binarios de los navegadores de Playwright
playwright install

```

---

## 💻 4. Ejecución del Pipeline de Datos

### Paso 1: Extraer opiniones crudas

```bash
python extractor.py

```

> [!WARNING]
> **Control de Sesión Obligatorio de Playwright:** Al ejecutar este comando, se abrirá automáticamente una ventana del navegador controlada por Playwright. **NO cierres esta ventana manualmente**. Está diseñada de forma visible únicamente para que procedas con el inicio de sesión manual, resolución de captchas o validaciones de identidad requeridas por la plataforma. Una vez completado el acceso con éxito, Playwright almacenará la persistencia de la sesión de forma local en cookies/almacenamiento seguro y el script continuará con la extracción automatizada en segundo plano.

### Paso 2: Enriquecer con IA local (Sentimiento y Categorías)

```bash
python clasificador.py

```

*Este módulo procesa las reseñas en bloques utilizando Ollama para generar etiquetas semánticas sin costo de APIs.*

### Paso 3: Limpiar e Indexar en ChromaDB con formato blindado de nodos

```bash
python indexador.py

```

*Este script elimina cualquier registro desactualizado de ChromaDB y construye la base de datos vectorial inyectando delimitadores de contexto para que el modelo no cruce autores.*

---

## 🎮 5. Interfaz del Asistente y Comandos Analíticos

Para iniciar el entorno interactivo de analítica de producto, ejecuta:

```bash
python asistente.py

```

Cuando la consola muestre la línea de comandos `escribe lo que quieres preguntar >`, puedes introducir consultas abiertas en lenguaje natural o forzar el enrutamiento nativo a nivel de metadatos en ChromaDB mediante los siguientes atallos integrados:

| Comando | Operación Técnica | Objetivo Analítico |
| --- | --- | --- |
| `/interfaz` | Filtro por `categoria == "Diseño e Interfaz"` | Aísla estética, ergonomía, colores y acabados visuales. |
| `/funcion` | Filtro por `categoria == "Funcionalidad"` | Evalúa el rendimiento operativo, conectividad y hardware. |
| `/negativos` | Filtro por `sentimiento == "Negativo"` | Identifica de forma masiva la totalidad de quejas y defectos. |
| `salir` | Cierre de sesión de la terminal | Finaliza el proceso interactivo y libera la memoria de Ollama. |

### 🛡️ Cláusula de Seguridad Sistémica (Anti-Alucinación)

El prompt sistémico integrado en el motor RAG prohíbe de forma estricta cualquier intento de invención o inferencia abstracta por parte de la IA local. Si realizas una consulta sobre una métrica o queja de la cual no existan evidencias verídicas y sólidas en los nodos recuperados por ChromaDB, el agente rechazará la deducción y responderá textualmente con la siguiente frase de control:

> *"No se cuenta con registros suficientes en las opiniones indexadas para responder a esta consulta específica."*

```

```
