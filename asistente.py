import os
import chromadb
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

class AsistenteAnaliticoHibrido:
    def __init__(self, ruta_db="chroma_db", nombre_coleccion="reviews_analizadas"):
        """
        Inicializa el motor RAG de ejecución local absoluta, conectándose a ChromaDB
        y levantando los modelos locales de Ollama para garantizar costo cero.
        """
        if not os.path.exists(ruta_db):
            raise FileNotFoundError(f"[ERROR] No se encontró el almacenamiento persistente en '{ruta_db}'. Ejecute 'indexador.py' primero.")

        print("[INFO] Cargando modelos locales en memoria (Ollama)...")
        self.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
        self.llm = Ollama(model="qwen2.5:1.5b", request_timeout=120.0)

        print("[INFO] Estableciendo conexión con ChromaDB...")
        db_cliente = chromadb.PersistentClient(path=ruta_db)
        chroma_collection = db_cliente.get_collection(name=nombre_coleccion)
        
        # Asociación de la base de datos persistente local con LlamaIndex
        self.vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        # Reconstrucción del índice desde el almacenamiento vectorial
        self.index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            storage_context=self.storage_context,
            embed_model=self.embed_model
        )

    def consultar(self, pregunta: str, filtro_categoria: str = None, filtro_sentimiento: str = None):
        """
        Ejecuta la recuperación híbrida local (Vectores + BM25) forzando el uso 
        del LLM local para evitar dependencias de OpenAI.
        """
        lista_filtros = []
        if filtro_categoria:
            lista_filtros.append(ExactMatchFilter(key="categoria", value=filtro_categoria))
        if filtro_sentimiento:
            lista_filtros.append(ExactMatchFilter(key="sentimiento", value=filtro_sentimiento))
            
        filtros = MetadataFilters(filters=lista_filtros) if lista_filtros else None

        # Configuración del recuperador vectorial base
        retriever_base = self.index.as_retriever(similarity_top_k=8, filters=filtros)
        
        # Fusión híbrida: Usamos "reciprocal_rerank", compatible con todas las versiones de LlamaIndex
        try:
            fusion_retriever = QueryFusionRetriever(
                [retriever_base],
                similarity_top_k=8,
                num_queries=1,
                llm=self.llm,
                mode="reciprocal_rerank"
            )
        except ValueError:
            # Respaldo absoluto sin parámetro de modo para delegar el control al framework
            fusion_retriever = QueryFusionRetriever(
                [retriever_base],
                similarity_top_k=8,
                num_queries=1,
                llm=self.llm
            )

        # Construcción del motor de respuestas fundamentado
        query_engine = RetrieverQueryEngine.from_args(
            retriever=fusion_retriever,
            llm=self.llm
        )

        prompt_sistemico = f"""
Actúa como un Consultor de Producto y Analista de Datos experto. Tu objetivo es responder la pregunta del usuario utilizando ÚNICAMENTE la información verídica y específica extraída de las reseñas proporcionadas en el contexto.

Normas estrictas de análisis:
1. Si los datos recuperados mencionan problemas explícitos, anomalías o componentes faltantes (ej. ausencia de cables de carga, retrasos logísticos, fallas estéticas o de conectividad), enuméralos con precisión y fundamenta tu respuesta en la reseña correspondiente.
2. Si la información recuperada no contiene datos suficientes para responder a la duda del cliente, responde textualmente: "No se cuenta con registros suficientes en las opiniones indexadas para responder a esta consulta específica". No asumas ni inventes métricas.
3. Mantén un tono técnico, objective, profesional y estructurado.

Pregunta de análisis: {pregunta}
""".strip()

        respuesta = query_engine.query(prompt_sistemico)
        return respuesta

if __name__ == "__main__":
    try:
        asistente = AsistenteAnaliticoHibrido()
    except Exception as e:
        print(f"[ERROR CRÍTICO] {e}")
        exit()

    print("\n" + "="*70)
    print("SISTEMA RAG DE ANALÍTICA DE PRODUCTO - ENTORNO DE AGENTE LOCAL")
    print("="*70)
    print("Instrucciones: Introduzca consultas abiertas o utilice comandos de filtro.")
    print("Comandos disponibles:")
    print("  /interfaz   - Filtra exclusivamente análisis de Diseño e Interfaz")
    print("  /funcion    - Filtra exclusivamente análisis de Funcionalidad")
    print("  /negativos  - Aísla únicamente opiniones de sentimiento Negativo")
    print("Para cerrar la sesión, escriba 'salir'.")
    print("="*70 + "\n")

    while True:
        entrada = input("escribe lo que quieres preguntar > ").strip()
        
        if entrada.lower() in ["salir", "exit", "quit"]:
            print("[INFO] Finalizando sesión del asistente analítico local.")
            break
            
        if not entrada:
            continue

        cat_filtro = None
        sent_filtro = None
        pregunta_final = entrada

        # Enrutamiento semántico por comandos de consola
        if entrada.startswith("/interfaz"):
            cat_filtro = "Diseño e Interfaz"
            pregunta_final = "Genera un reporte analítico sobre la percepción visual, ergonomía, estética y acabados del producto."
            print(f"[FILTRO APLICADO] Restringido a categoría: {cat_filtro}")
            
        elif entrada.startswith("/funcion"):
            cat_filtro = "Funcionalidad"
            pregunta_final = "Genera un reporte técnico enfocado en el rendimiento operativo, conectividad y fallas mecánicas/lógicas."
            print(f"[FILTRO APLICADO] Restringido a categoría: {cat_filtro}")
            
        elif entrada.startswith("/negativos"):
            sent_filtro = "Negativo"
            pregunta_final = "Identifica de forma detallada la totalidad de quejas, inconformidades y defectos reportados por los usuarios."
            print(f"[FILTRO APLICADO] Restringido a sentimiento: {sent_filtro}")

        print("[PROCESAMIENTO] Consultando índices híbridos y generando respuesta...")
        
        try:
            resultado = asistente.consultar(
                pregunta=pregunta_final, 
                filtro_categoria=cat_filtro, 
                filtro_sentimiento=sent_filtro
            )
            print(f"\n[INFORME GENERADO]\n{resultado}\n")
        except Exception as e:
            print(f"[ERROR] Ocurrió una excepción durante la ejecución: {e}\n")
            
        print("-" * 70)