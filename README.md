# 🧠 Agente Local de Analítica de Reseñas (Smart RAG Engine + API)

Sistema profesional de procesamiento, enriquecimiento y análisis de lenguaje natural orientado a auditorías de producto, inteligencia comercial y análisis de opiniones. 

El proyecto opera bajo una **Arquitectura de Microservicios Web** (FastAPI) en un entorno **100% local, privado y libre de dependencias externas de inferencia**, garantizando:

* Máxima confidencialidad de datos (Seguridad JWT y Hasheo Bcrypt).
* Costo operativo nulo (Inferencia completamente offline mediante Ollama).
* Streaming de Tokens en Tiempo Real (Server-Sent Events).
* Observabilidad y telemetría de rendimiento local (TTFT, TPS).
* Protección contra Inyección de Prompts (Guardrails).

---

## 🏗️ 1. Arquitectura General y Flujo de Datos

El pipeline ha evolucionado de un script de terminal a un Backend robusto desacoplado en dominios. La entrada principal ahora es web (`api.py`), que gestiona la seguridad, delega la búsqueda híbrida y transmite la respuesta en tiempo real al Frontend (React).

```text
                        ┌──────────────────────────────┐
                        │      Frontend (React)        │
                        └──────────────┬───────────────┘
                                  (HTTP / SSE)
                                       ▼
                        ┌──────────────────────────────┐
                        │       api.py (FastAPI)       │
                        │    [Orquestador Central]     │
                        └──────┬───────────────┬───────┘
                               │               │
                     [Autenticación JWT]  [Guardrails] 
                               │               │
                               ▼               ▼
                   ┌───────────────────────────────────┐
                   │    modulos/agente/asistente.py    │
                   │    (Flujo LlamaIndex Workflows)   │
                   └───────┬───────────────────┬───────┘
                           │                   │
                           ▼                   ▼
           ┌───────────────────────┐   ┌───────────────────────┐
           │ modulos/rutas/        │   │ modulos/              │
           │ herramientas_api.py   │   │ procesamiento/        │
           │ (Músculos y Reportes) │   │ (Indexador Híbrido)   │
           └───────────────────────┘   └───────────────────────┘
```

## 📁 2. Estructura Limpia del Proyecto (Domain-Driven Design)

El código se organiza bajo el Principio de Responsabilidad Única (SRP):

```text
AgenteLocalParaResenas/
│
├── api.py                    # 🚪 PUERTA WEB: Servidor FastAPI, Autenticación y SSE.
├── main.py                   # 🖥️ PUERTA CLI: Ejecución y pruebas en terminal local.
│
├── datos/                    # 🗄️ CAPA DE PERSISTENCIA
│   ├── base_relacional/      #   └── historial_sesiones.db (Usuarios, Mensajes, Auditoría)
│   ├── base_vectorial/       #   └── chroma.sqlite3 (Embeddings)
│   ├── crudos/               #   └── reseñas_crudas.json
│   └── procesados/           #   └── reseñas_enriquecidas.json
│
└── modulos/                  # 🧠 CAPA DE NEGOCIO Y DOMINIOS
    │
    ├── agente/               # 🤖 DOMINIO DE IA (asistente.py, herramientas.py)
    ├── infraestructura/      # 🔌 DOMINIO DE BD (clientes_sqlite.py)
    ├── procesamiento/        # ⚙️ DOMINIO ETL (extractor.py, clasificador.py, indexador.py)
    ├── rutas/                # 🛣️ DOMINIO DE API (herramientas_api.py)
    └── seguridad/            # 🛡️ DOMINIO DE PROTECCIÓN (autenticacion.py, guardrails.py)
```

## 🔄 3. Fases del Pipeline de Datos

* **Extracción (Scraping):** Obtención del DOM (Amazon/MercadoLibre) vía Playwright.
* **Enriquecimiento Semántico:** Clasificación de sentimientos y categorías vía Qwen 2.5 local.
* **Indexación Vectorial:** Generación de embeddings con `nomic-embed-text` hacia ChromaDB usando similitud de coseno.
* **Recuperación Inteligente (Híbrida):** Búsqueda Vectorial + Búsqueda Léxica (BM25) fusionadas mediante Reciprocal Rank Fusion (RRF).

## 🛡️ 4. Seguridad, UX y Observabilidad (Fase Avanzada)

El sistema integra características propias de Machine Learning Operations (MLOps):

* **Autenticación Stateless:** Tokens JWT (JSON Web Tokens) y contraseñas hasheadas en bcrypt. Eliminación en cascada de historiales de chat.
* **Guardrails (Capa de Validación):** Middleware que intercepta Prompt Injections ("Olvida tus instrucciones") bloqueando la solicitud antes de gastar procesamiento en la IA.
* **Telemetría en SQLite (Auditoría):** Registro automático y milimétrico de:
  * `ttft_ms`: Time To First Token (Latencia de inicio).
  * `tokens_per_second`: Velocidad de inferencia del procesador.
  * `total_latency_ms` y bloqueos de seguridad.
* **Streaming SSE Real y Filtro ReAct:** Transmisión asíncrona de tokens nativa. El backend oculta la "cháchara mental" del modelo (Thoughts/Actions) y emite banderas `[[SYS_TOOL]]` y `[[SYS_STREAM_START]]` para que el frontend renderice esqueletos de carga dinámicos.

## 🛠️ 5. Requisitos e Instalación

### Ollama (Modelos Locales)
```bash
ollama pull qwen2.5:1.5b
ollama pull nomic-embed-text
```

### Dependencias Python
```text
fastapi
uvicorn
passlib[bcrypt]
python-jose[cryptography]
chromadb>=0.4.22
llama-index-core>=0.14.0
llama-index-vector-stores-chroma
llama-index-embeddings-ollama
llama-index-llms-ollama
llama-index-retrievers-bm25
playwright
```

### Despliegue Local

1. **Entorno Virtual:** `python -m venv venv` y actívalo (`.\venv\Scripts\Activate.ps1`).
2. **Instalación:** `pip install -r requirements.txt` y `playwright install chromium`.
3. **Levantar Servidor API (FastAPI):**
```bash
   uvicorn api:app --reload
   ```
   *La API estará disponible en `http://127.0.0.1:8000`.*

## 🎮 6. Interacción y Function Calling Local

El Agente no solo platica, también ejecuta código Python físico en la computadora del host dependiendo de la necesidad:

* **Herramientas Internas (Vía Chat):** El LLM usa `analizador_de_resenas` para navegar por ChromaDB.
* **Herramientas Externas (Vía API Endpoints):** El Frontend puede disparar rutas como `/api/herramientas/exportar-csv` para interactuar con archivos en Windows sin despertar al modelo de IA, ahorrando ciclos de CPU.

### Exportación Compatible
Los archivos CSV generados inyectan BOM (`utf-8-sig`) para compatibilidad perfecta con acentos y eñes en Microsoft Excel.

## 📌 Stack Tecnológico

| Dominio | Tecnología |
|---|---|
| **Backend API** | FastAPI, Uvicorn, Python 3.11+ |
| **Seguridad** | JWT, Passlib (Bcrypt), Middlewares |
| **Inferencia** | Ollama, Qwen 2.5 (1.5B), Nomic Embeddings |
| **RAG / NLP** | LlamaIndex Workflows, ChromaDB, BM25 |
| **Persistencia** | SQLite (Relacional), Chroma (Vectorial) |
| **ETL / Web** | Playwright |