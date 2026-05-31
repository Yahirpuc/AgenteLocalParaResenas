# 🧠 Agente Local de Analítica de Reseñas (RAG Engine)

Sistema profesional de procesamiento y análisis de lenguaje natural orientado a opiniones de usuarios y activos de información textual.

El proyecto opera bajo un entorno **100% local, privado y sin dependencias de APIs externas**, garantizando:

* Máxima confidencialidad de datos
* Costo operativo cero
* Persistencia local de embeddings y sesiones
* Inferencia completamente offline mediante Ollama

---

# 🏗️ 1. Arquitectura General y Flujo de Datos

El pipeline está completamente unificado y automatizado a través de un orquestador central que administra el ciclo de vida de los datos sin requerir ejecuciones manuales por separado.

```text
               ┌──────────────────────────────┐
               │         python main.py       │
               └──────────────┬───────────────┘
                              │
            [¿Existe Base de Datos Vectorial?]
               /                             \
        (No / Opción /reiniciar)            (Sí)
             /                                 \
            ▼                                   ▼
   [extractor.py (Universal)]          [asistente.py (Chat Local)]
            │                                   ▲
            ▼                                   │
(reseñas_enriquecidas.json)                     │
            │                                   │
            ▼                                   │
  [indexador.py (ChromaDB)] ────────────────────┘
```

## Componentes

### `main.py` (Orquestador Central)

Punto de entrada unificado del sistema. Se encarga de:

* Verificar de forma inteligente si ya existen datos indexados previamente para saltar directo al asistente en menos de 3 segundos.
* Controlar el flujo automatizado entre la extracción de datos, la inyección en la base de datos vectorial y la apertura de la interfaz del chat.
* Administrar el comando avanzado `/reiniciar`, el cual purga las colecciones internas *in-place* de forma segura, evitando bloqueos de permisos con Windows (`WinError 32`) y permitiendo cambiar de URL al vuelo.

---

### `extractor.py` (Motor Universal Heurístico)

Responsable de:

* Analizar el DOM de cualquier página web de forma semántica al vuelo, sin depender de selectores CSS fijos.
* Aislar bloques de texto mediante densidad de caracteres.
* Extraer autores, opiniones y puntuaciones mediante expresiones regulares.
* Mantener sesiones autenticadas utilizando el directorio aislado `sesion_playwright`, evitando inicios de sesión repetitivos y captchas en plataformas como Amazon o Mercado Libre.

Produce:

```text
reseñas_enriquecidas.json
```

---

### `indexador.py`

Responsable de:

* Formatear el contexto utilizando delimitadores estrictos para evitar contaminación entre documentos.
* Generar embeddings vectoriales locales.
* Inyectar los datos en ChromaDB.
* Limpiar colecciones anteriores para evitar duplicados.

Tecnologías utilizadas:

* `nomic-embed-text`
* `ChromaDB`
* `LlamaIndex`

Persistencia:

```text
/chroma_db
```

---

### `asistente.py`

Interfaz conversacional RAG híbrida que combina:

#### Recuperación Vectorial

Captura el sentido semántico y el contexto general mediante embeddings.

#### Búsqueda BM25 Lexical

Captura palabras clave, términos y marcas exactas letra por letra.

#### Fusión Híbrida

Implementa **Reciprocal Rank Fusion (RRF)** para combinar los resultados de ambos recuperadores y mejorar la precisión.

#### Routing por Metadatos

Filtra el contexto antes de realizar la búsqueda para aislar categorías específicas de forma estricta.

---

# 🛠️ 2. Requisitos del Sistema

## A. Ollama (Obligatorio)

Este proyecto requiere:

* Ollama instalado.
* Servicio de Ollama ejecutándose en segundo plano.

Sitio oficial:

```text
https://ollama.com/
```

Descargar los modelos necesarios:

```bash
# Modelo de inferencia y chat
ollama pull qwen2.5:1.5b

# Modelo de embeddings
ollama pull nomic-embed-text
```

---

## B. Dependencias Python

Instalar:

```text
chromadb>=0.4.0
llama-index-core
llama-index-vector-stores-chroma
llama-index-embeddings-ollama
llama-index-llms-ollama
llama-index-retrievers-bm25
bm25s
rank_bm25
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

### Windows (PowerShell)

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

# 📦 4. Ejecución del Pipeline Unificado

Todo el proceso está centralizado en un único comando:

```bash
python main.py
```

## Flujo Automatizado

### Primera ejecución

1. El sistema detecta que no existen índices guardados.
2. Solicita la URL del producto.
3. Inicia Playwright.

### Pausa de Control Manual

1. Navega hasta la sección de reseñas.
2. Deja visibles las opiniones.
3. Espera unos segundos para estabilizar el DOM.
4. Presiona `ENTER` en la terminal.

### Indexación automática

1. El extractor recopila el contenido.
2. El indexador genera embeddings.
3. Se almacenan en ChromaDB.
4. Se abre automáticamente el asistente conversacional.

### Ejecuciones posteriores

Si la base vectorial ya existe:

* Se omite el raspado.
* Se omite la indexación.
* Se abre directamente el chat local en pocos segundos.

---

# 🎮 5. Uso del Asistente Analítico

Cuando el sistema esté listo aparecerá:

```text
escribe lo que quieres preguntar >
```

El usuario puede realizar consultas abiertas aprovechando la combinación de búsqueda semántica y lexical.

El modelo está restringido para responder únicamente utilizando la información contenida en el contexto recuperado.

---

# ⚡ 6. Comandos Integrados

| Comando      | Función Técnica                       | Objetivo                                                         |
| ------------ | ------------------------------------- | ---------------------------------------------------------------- |
| `/interfaz`  | `categoria == "Diseño e Interfaz"`    | Reporte analítico sobre percepción visual, ergonomía y acabados  |
| `/funcion`   | `categoria == "Rendimiento y Caídas"` | Reporte técnico enfocado en rendimiento operativo y conectividad |
| `/negativos` | `sentimiento == "Negativo"`           | Identificación detallada de quejas reportadas                    |
| `/reiniciar` | `asistente.cerrar_conexion()`         | Vacía la base vectorial y solicita una nueva URL                 |
| `salir`      | Finaliza la sesión                    | Libera recursos y cierra Ollama                                  |

---

# 🛡️ 7. Sistema Anti-Alucinación

El sistema incorpora un prompt estricto bajo el estándar ChatML.

Si la información solicitada no existe dentro del contexto recuperado, la respuesta obligatoria será:

> "No se cuenta con registros suficientes en las opiniones indexadas para responder a esta consulta específica."

---

# 📁 Estructura Recomendada del Proyecto

```text
proyecto-rag/
│
├── main.py
├── extractor.py
├── indexador.py
├── asistente.py
│
├── reseñas_enriquecidas.json
│
├── chroma_db/
├── sesion_playwright/
│
├── requirements.txt
└── venv/
```

---

# 🔒 Características Clave

* **100% Local y Privado**
* **Costo Operativo Cero**
* **Procesamiento Offline**
* **Embeddings Locales**
* **Buscador Híbrido Vectorial + BM25**
* **Persistencia de Sesiones con Playwright**
* **Recuperación Semántica de Alta Precisión**
* **Vaciado Seguro de Índices en Windows**
* **Arquitectura RAG Empresarial Offline**

---

# 📌 Stack Tecnológico

| Tecnología       | Función                   |
| ---------------- | ------------------------- |
| Ollama           | Inferencia local          |
| Qwen2.5:1.5b     | Generación y análisis NLP |
| nomic-embed-text | Embeddings vectoriales    |
| ChromaDB         | Base de datos vectorial   |
| LlamaIndex       | Orquestación RAG          |
| BM25             | Recuperación lexical      |
| Playwright       | Automatización web        |
| Python           | Backend principal         |

---

# ✅ Estado del Proyecto

Actualmente preparado para:

* Analítica universal de reseñas en plataformas de comercio electrónico.
* Sistemas RAG privados empresariales.
* Entornos sin dependencia de servicios externos.
* Procesamiento local de lenguaje natural con costo operativo cero.
* Recuperación híbrida semántica y lexical de alta precisión.
