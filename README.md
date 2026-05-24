# 🧠 Agente Local de Analítica de Reseñas (RAG Engine)

Sistema profesional de procesamiento y análisis de lenguaje natural orientado a opiniones de usuarios y activos de información textual.

El proyecto opera bajo un entorno **100% local, privado y sin dependencias de APIs externas**, garantizando:

- Máxima confidencialidad de datos
- Costo operativo cero
- Persistencia local de embeddings y sesiones
- Inferencia completamente offline mediante Ollama

---

# 🏗️ 1. Arquitectura General y Flujo de Datos

El pipeline está desacoplado en cuatro fases independientes para optimizar memoria RAM, escalabilidad y mantenimiento.

```text
[extractor.py]
│
▼
(reseñas_crudas.json)

[clasificador.py]
│
▼
(reseñas_enriquecidas.json)

[indexador.py]
│
▼
(chroma_db/)

[asistente.py]
```

## Componentes

### `extractor.py`
Responsable de:

- Automatización con Playwright
- Persistencia de sesiones autenticadas
- Extracción de opiniones
- Mitigación de bloqueos y captchas

Produce:

```text
reseñas_crudas.json
```

---

### `clasificador.py`

Motor de enriquecimiento semántico mediante:

- `qwen2.5:1.5b`
- Inferencia local con Ollama
- Clasificación por sentimiento
- Categorización analítica

Produce:

```text
reseñas_enriquecidas.json
```

---

### `indexador.py`

Responsable de:

- Formateo blindado de contexto
- Generación de embeddings
- Persistencia vectorial en ChromaDB
- Limpieza automática de registros obsoletos

Utiliza:

- `nomic-embed-text`
- `ChromaDB`
- `LlamaIndex`

Persistencia:

```text
/chroma_db
```

---

### `asistente.py`

Interfaz conversacional RAG híbrida:

- Recuperación vectorial semántica
- Búsqueda BM25 lexical
- Routing por comandos
- Respuestas controladas anti-alucinación

---

# 🛠️ 2. Requisitos del Sistema

## A. Ollama (Obligatorio)

Este proyecto requiere tener instalado:

- Ollama
- Servicio activo en segundo plano

Sitio oficial:

```text
https://ollama.com/
```

Descarga los modelos necesarios:

```bash
# Modelo de inferencia y clasificación
ollama pull qwen2.5:1.5b

# Modelo de embeddings semánticos
ollama pull nomic-embed-text
```

---

## B. Dependencias Python

Crea un archivo:

```text
requirements.txt
```

Contenido:

```text
chromadb>=0.4.0
llama-index-core
llama-index-vector-stores-chroma
llama-index-embeddings-ollama
llama-index-llms-ollama
playwright
```

---

# 🚀 3. Instalación del Entorno

## Crear entorno virtual

```bash
python -m venv venv
```

---

## Activar entorno virtual

### Windows / PowerShell

```bash
.\venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
source venv/bin/activate
```

---

## Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## Instalar navegadores de Playwright

```bash
playwright install
```

---

# 📦 4. Ejecución del Pipeline

---

## Paso 1 — Extracción de Opiniones

```bash
python extractor.py
```

### ⚠️ Importante — Sesión Visual de Playwright

Al ejecutar este módulo:

- Se abrirá un navegador controlado por Playwright
- NO debes cerrarlo manualmente
- Está diseñado para:
  - Login manual
  - Resolución de captchas
  - Verificaciones de identidad

Una vez autenticado:

- La sesión será persistida localmente
- El scraping continuará automáticamente

---

## Paso 2 — Clasificación y Enriquecimiento IA

```bash
python clasificador.py
```

Este módulo:

- Procesa opiniones por lotes
- Ejecuta inferencia local
- Genera metadatos analíticos
- No utiliza APIs externas

---

## Paso 3 — Indexación Vectorial

```bash
python indexador.py
```

Este proceso:

- Elimina registros obsoletos
- Reconstruye ChromaDB
- Genera embeddings semánticos
- Inserta delimitadores estrictos de contexto

Ejemplo de estructura blindada:

```text
AUTOR:
Juan Pérez

TEXTO DE LA OPINIÓN:
"La batería dura muy poco..."
```

Esto evita:

- Mezcla de autores
- Contaminación contextual
- Respuestas cruzadas incorrectas

---

# 🎮 5. Uso del Asistente Analítico

Inicia la consola interactiva:

```bash
python asistente.py
```

Cuando aparezca:

```text
escribe lo que quieres preguntar >
```

Puedes realizar:

- Consultas abiertas en lenguaje natural
- Filtros semánticos directos
- Búsquedas por categoría o sentimiento

---

# ⚡ 6. Comandos Integrados

| Comando | Función Técnica | Objetivo |
|---|---|---|
| `/interfaz` | `categoria == "Diseño e Interfaz"` | Analiza estética, ergonomía y acabados visuales |
| `/funcion` | `categoria == "Funcionalidad"` | Evalúa desempeño operativo y hardware |
| `/negativos` | `sentimiento == "Negativo"` | Detecta quejas y defectos críticos |
| `salir` | Finaliza la sesión | Libera memoria y termina Ollama |

---

# 🛡️ 7. Sistema Anti-Alucinación

El motor RAG incorpora un prompt sistémico restrictivo que:

- Prohíbe inferencias no verificadas
- Impide fabricación de datos
- Exige evidencia recuperada desde ChromaDB

Si no existen suficientes registros válidos, el sistema responderá:

> "No se cuenta con registros suficientes en las opiniones indexadas para responder a esta consulta específica."

---

# 📁 Estructura Recomendada del Proyecto

```text
proyecto-rag/
│
├── extractor.py
├── clasificador.py
├── indexador.py
├── asistente.py
│
├── reseñas_crudas.json
├── reseñas_enriquecidas.json
│
├── chroma_db/
│
├── requirements.txt
│
└── venv/
```

---

# 🔒 Características Clave

- 100% Local
- Sin APIs externas
- Persistencia en disco
- Embeddings privados
- Motor híbrido RAG + BM25
- Playwright persistente
- ChromaDB vectorial
- Inferencia offline con Ollama
- Arquitectura desacoplada
- Protección anti-alucinación

---

# 📌 Stack Tecnológico

| Tecnología | Función |
|---|---|
| Ollama | Inferencia local |
| Qwen2.5 | Clasificación NLP |
| nomic-embed-text | Embeddings |
| ChromaDB | Base vectorial |
| LlamaIndex | Orquestación RAG |
| Playwright | Automatización web |
| Python | Backend principal |

---

# ✅ Estado del Proyecto

Sistema preparado para:

- Analítica de reseñas
- Inteligencia de producto
- Minería de opiniones
- Detección de problemas recurrentes
- Estudios de percepción de usuarios
- Sistemas RAG privados empresariales
