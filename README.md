# 🧠 Agente Local de Analítica de Reseñas (Smart RAG Engine)

Sistema profesional de procesamiento, enriquecimiento y análisis de lenguaje natural orientado a auditorías de producto, inteligencia comercial y análisis de opiniones en plataformas de comercio electrónico.

El proyecto opera bajo un entorno **100% local, privado y libre de dependencias externas de inferencia**, garantizando:

* Máxima confidencialidad de datos.
* Costo operativo prácticamente nulo.
* Persistencia local de embeddings, registros y sesiones.
* Inferencia completamente offline mediante Ollama.
* Control total sobre el ciclo de vida de la información procesada.

---

# 🏗️ 1. Arquitectura General y Flujo de Datos

El pipeline se encuentra desacoplado en múltiples fases especializadas: extracción estructurada, enriquecimiento semántico mediante LLM, indexación híbrida y recuperación inteligente con soporte para Function Calling local.

```text
                        ┌──────────────────────────────┐
                        │       python main.py         │
                        └──────────────┬───────────────┘
                                       │
                    [¿Existe Base de Datos Vectorial?]
                       /                           \
             (No / Comando /reiniciar)             (Sí)
                    /                                 \
                   ▼                                   ▼
       ┌────────────────────────┐        ┌────────────────────────┐
       │ extractor_especifico   │        │      asistente.py      │
       │ (Selectores Nativos)   │        │   Chat Interactivo     │
       └────────────┬───────────┘        └────────────▲───────────┘
                    │                                │
                    ▼                                │
         (reseñas_crudas.json)                       │
                    │                                │
                    ▼                                │
       ┌────────────────────────┐                    │
       │    clasificador.py     │                    │
       │ (Inferencia con Qwen)  │                    │
       └────────────┬───────────┘                    │
                    │                                │
                    ▼                                │
     (reseñas_enriquecidas.json)                     │
                    │                                │
                    ▼                                │
       ┌────────────────────────┐                    │
       │      indexador.py      │────────────────────┘
       │   ChromaDB + Cosine    │
       └────────────────────────┘
```

### Evolución de la Arquitectura

El proyecto incorpora además un módulo experimental denominado:

```text
extractor_universal.py
```

Este componente se encuentra actualmente en fase de investigación y pruebas avanzadas. Su objetivo es reemplazar la dependencia de selectores específicos mediante técnicas heurísticas capaces de identificar reseñas en cualquier sitio web de forma automática.

Actualmente, el entorno de producción utiliza `extractor_especifico.py` por su mayor estabilidad y precisión. Sin embargo, `extractor_universal.py` representa la siguiente etapa evolutiva del proyecto y será integrado en versiones futuras como motor de extracción multiplataforma.

---

# 🔄 2. Fases del Pipeline

## Fase 1 — Extracción de Datos Crudos

Obtención de información directamente desde el DOM de la plataforma de comercio electrónico.

**Entrada:**

```text
Página web del producto
```

**Salida:**

```text
reseñas_crudas.json
```

El archivo contiene exclusivamente información original extraída de los comentarios de los usuarios sin ningún procesamiento semántico adicional.

---

## Fase 2 — Enriquecimiento Semántico

Procesamiento del dataset mediante un modelo local ejecutado en Ollama.

Durante esta fase, el sistema analiza cada reseña y genera metadatos estructurados.

### Información generada

#### Sentimiento

Clasificación estricta en:

* Positivo
* Neutral
* Negativo

#### Categoría Semántica

Asignación automática a categorías como:

* Rendimiento y Caídas
* Diseño e Interfaz
* Materiales y Durabilidad
* Precio y Valor
* Logística y Envío
* Calidad General
* Experiencia de Usuario
* Compatibilidad
* Instalación y Configuración

**Salida:**

```text
reseñas_enriquecidas.json
```

---

## Fase 3 — Indexación Vectorial

Conversión de documentos enriquecidos en representaciones vectoriales para recuperación semántica.

Tecnologías utilizadas:

* ChromaDB
* LlamaIndex
* nomic-embed-text

Persistencia:

```text
/chroma_db
```

---

## Fase 4 — Recuperación Inteligente

Combinación de múltiples estrategias de búsqueda:

### Recuperación Vectorial

Captura contexto, intención y similitud semántica.

### Recuperación Léxica (BM25)

Prioriza coincidencias exactas de palabras clave.

### Reciprocal Rank Fusion (RRF)

Fusiona ambos resultados para maximizar precisión y relevancia.

---

# 🧩 3. Componentes del Ecosistema

## 🎛️ `main.py` (Orquestador Central)

Punto de entrada principal de la aplicación.

Responsabilidades:

* Verificar la existencia de la base vectorial persistente.
* Automatizar el flujo completo de extracción, clasificación e indexación.
* Reducir los tiempos de inicio cuando ya existen datos indexados.
* Gestionar el comando `/reiniciar`.
* Implementar mecanismos de protección contra bloqueos de SQLite en Windows.

---

## 🕷️ `extractor_especifico.py`

Motor de extracción basado en Playwright y selectores nativos.

### Amazon México

* Extracción mediante nodos `[data-hook="review"]`.
* Eliminación de ruido visual y elementos decorativos.

### Mercado Libre

* Lectura automática de comentarios.
* Interpretación de puntuaciones mediante atributos `aria-label`.
* Expansión automática de todos los botones **"Leer más"** antes del análisis del DOM.

Salida:

```text
reseñas_crudas.json
```

---

## 🧠 `clasificador.py`

Módulo de enriquecimiento semántico ejecutado localmente mediante Qwen.

Funciones:

* Clasificación de sentimiento.
* Categorización temática.
* Normalización de datos.
* Generación de metadatos estructurados.

Salida:

```text
reseñas_enriquecidas.json
```

---

## 🗄️ `indexador.py`

Constructor del índice híbrido.

Características:

* Delimitación estricta de documentos.
* Prevención de contaminación contextual.
* Persistencia vectorial local.
* Configuración explícita de similitud coseno.

```python
{"hnsw:space": "cosine"}
```

---

## 💬 `asistente.py`

Motor principal de recuperación y generación.

Implementa:

* Recuperación vectorial.
* Recuperación BM25.
* Fusión RRF.
* Routing por metadatos.
* Function Calling local.

---

# 🛠️ 4. Requisitos del Sistema

## Ollama

Instalar Ollama y descargar los modelos requeridos:

```bash
# Modelo principal de clasificación y análisis
ollama pull qwen2.5:1.5b

# Modelo de embeddings
ollama pull nomic-embed-text
```

---

## Dependencias Python

```text
chromadb>=0.4.22
llama-index-core
llama-index-vector-stores-chroma
llama-index-embeddings-ollama
llama-index-llms-ollama
llama-index-retrievers-bm25
rank_bm25
bm25s
playwright
```

---

# 🚀 5. Instalación y Despliegue

## Crear entorno virtual

```bash
python -m venv venv
```

### Windows

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

## Instalar Chromium

```bash
playwright install chromium
```

---

## Ejecutar el sistema

```bash
python main.py
```

---

# 🎮 6. Interfaz del Chat e Intercepción de Acciones

Prompt principal:

```text
Pregunta sobre las reseñas >
```

## Filtros RAG por Metadatos

| Comando      | Acción                                                     |
| ------------ | ---------------------------------------------------------- |
| `/interfaz`  | Filtra exclusivamente la categoría Diseño e Interfaz       |
| `/funcion`   | Filtra Rendimiento y Caídas                                |
| `/negativos` | Filtra únicamente opiniones negativas                      |
| `/reiniciar` | Reinicia completamente el entorno y solicita una nueva URL |

---

## Function Calling Local

El sistema puede interceptar solicitudes específicas y ejecutar herramientas Python en lugar de generar una respuesta tradicional.

### Ejemplos

```text
cuenta los sentimientos totales
→ contar_sentimientos_totales()

calcula el promedio de estrellas
→ calcular_promedio_estrellas()

exporta las opiniones a CSV
→ exportar_analisis_csv()

guarda un reporte en TXT
→ guardar_reporte_txt()
```

### Exportación Compatible con Excel

Los archivos CSV son generados utilizando:

```text
utf-8-sig
```

Esto garantiza compatibilidad completa con Microsoft Excel, preservando correctamente:

* Acentos
* Ñ y ñ
* Caracteres especiales
* Separación correcta de columnas

---

# 🛡️ 7. Sistema Anti-Alucinación

El agente opera bajo un prompt de sistema estricto basado en ChatML.

Cuando no exista evidencia suficiente dentro del contexto recuperado, responderá obligatoriamente:

> "No se cuenta con registros suficientes en las opiniones indexadas para responder a esta consulta específica."

No se permite inferir, inventar ni extrapolar información fuera de los documentos recuperados.

---

# 📁 Estructura del Proyecto

```text
proyecto-rag/
│
├── main.py
├── extractor_especifico.py
├── extractor_universal.py
├── clasificador.py
├── indexador.py
├── asistente.py
├── funciones_locales.py
│
├── reseñas_crudas.json
├── reseñas_enriquecidas.json
│
├── chroma_db/
├── sesion_playwright/
│
├── requirements.txt
└── README.md
```

---

# 🔒 Características Principales

* Procesamiento completamente local.
* Arquitectura RAG híbrida empresarial.
* Recuperación Vectorial + BM25 + RRF.
* Function Calling local.
* Persistencia de sesiones Playwright.
* Compatibilidad con Windows, Linux y macOS.
* Protección contra bloqueos SQLite.
* Exportación de reportes analíticos.
* Sin dependencias de APIs externas.
* Costo operativo cero.

---

# 📌 Stack Tecnológico

| Tecnología       | Función                      |
| ---------------- | ---------------------------- |
| Python           | Backend principal            |
| Ollama           | Inferencia local             |
| Qwen 2.5         | Clasificación y análisis NLP |
| nomic-embed-text | Embeddings semánticos        |
| ChromaDB         | Base de datos vectorial      |
| LlamaIndex       | Orquestación RAG             |
| BM25             | Recuperación léxica          |
| Playwright       | Automatización web           |
| SQLite           | Persistencia local           |

---

# ✅ Estado del Proyecto

### Estado Actual

* Extracción estructurada estable.
* Clasificación semántica operativa.
* Recuperación híbrida implementada.
* Function Calling local funcional.
* Persistencia vectorial consolidada.

### Próximas Iteraciones

* Integración completa de `extractor_universal.py`.
* Expansión de categorías semánticas.
* Dashboards analíticos locales.
* Generación automática de reportes ejecutivos.
* Soporte para múltiples plataformas de comercio electrónico.

Proyecto preparado para escenarios académicos, auditorías empresariales, inteligencia competitiva y sistemas RAG privados de producción.
