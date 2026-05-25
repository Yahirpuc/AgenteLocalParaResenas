import os
import chromadb
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.retrievers.bm25 import BM25Retriever

class AsistenteAnaliticoHibrido:
    def __init__(self, ruta_db="chroma_db", nombre_coleccion="reviews_analizadas"):
        """
        Inicializa el motor RAG de ejecución local absoluta, conectándose a ChromaDB,
        reconstruyendo los nodos e inicializando los modelos de Ollama.
        """
        if not os.path.exists(ruta_db):
            raise FileNotFoundError(f"[ERROR] No se encontró el almacenamiento persistente en '{ruta_db}'. Ejecute 'indexador.py' primero.")

        print("[INFO] Cargando modelos locales en memoria (Ollama)...")
        self.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
        self.llm = Ollama(model="qwen2.5:1.5b", request_timeout=120.0)

        print("[INFO] Estableciendo conexión con ChromaDB...")
        db_cliente = chromadb.PersistentClient(path=ruta_db)
        
        # Guardamos la colección nativa de chroma en una variable de la clase
        self.chroma_collection = db_cliente.get_collection(name=nombre_coleccion)
        
        # Asociación de la base de datos persistente local con LlamaIndex
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        # Reconstrucción del índice desde el almacenamiento vectorial
        self.index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            storage_context=self.storage_context,
            embed_model=self.embed_model
        )
      #Descargar los textos reales directo de ChromaDB y convertirlos en Nodos de LlamaIndex
        print("[INFO] Recuperando documentos de ChromaDB para el motor de palabras clave (BM25)...")
        from llama_index.core.schema import TextNode
        
        datos_chroma = self.chroma_collection.get()
        self.nodos_documentos = []
        
        # Reconstruimos la lista de nodos dinámicamente con los textos e IDs reales de tu BD
        for texto, id_doc, metadato in zip(datos_chroma['documents'], datos_chroma['ids'], datos_chroma['metadatas']):
            self.nodos_documentos.append(
                TextNode(text=texto, id_=id_doc, metadata=metadato)
            )
        print(f"[INFO] Éxito: {len(self.nodos_documentos)} nodos cargados en el motor BM25.")
    def consultar(self, pregunta: str, filtro_categoria: str = None, filtro_sentimiento: str = None):
        """
        Ejecuta la recuperación híbrida local real combinando vectores y BM25,
        asegurando que el prompt estructurado se aplique correctamente sobre el contexto.
        """
        from llama_index.core.response_synthesizers import CompactAndRefine
        from llama_index.core import PromptTemplate

        lista_filtros = []
        if filtro_categoria:
            lista_filtros.append(ExactMatchFilter(key="categoria", value=filtro_categoria))
        if filtro_sentimiento:
            lista_filtros.append(ExactMatchFilter(key="sentimiento", value=filtro_sentimiento))
            
        filtros = MetadataFilters(filters=lista_filtros) if lista_filtros else None

        # 1. Recuperador Vectorial (Aplica filtros nativos en Chroma)
        retriever_vectorial = self.index.as_retriever(similarity_top_k=5, filters=filtros)
        
        # 2. Recuperador BM25 Filtrado dinámicamente en memoria para evitar mezclas
        nodos_filtrados = self.nodos_documentos
        if filtro_categoria or filtro_sentimiento:
            nodos_filtrados = []
            for nodo in self.nodos_documentos:
                cumple = True
                if filtro_categoria and nodo.metadata.get("categoria") != filtro_categoria:
                    cumple = False
                if filtro_sentimiento and nodo.metadata.get("sentimiento") != filtro_sentimiento:
                    cumple = False
                if cumple:
                    nodos_filtrados.append(nodo)
        
        # Si el filtro dejó vacío al BM25, usamos un fallback seguro para que no truene
        if not nodos_filtrados:
            retriever_bm25 = retriever_vectorial
        else:
            retriever_bm25 = BM25Retriever.from_defaults(nodes=nodos_filtrados, similarity_top_k=5)
        
        # 3. Fusión Híbrida Real
        try:
            fusion_retriever = QueryFusionRetriever(
                [retriever_vectorial, retriever_bm25],
                similarity_top_k=5,
                num_queries=1,
                llm=self.llm,
                mode="reciprocal_rerank"
            )
        except ValueError:
            fusion_retriever = QueryFusionRetriever(
                [retriever_vectorial, retriever_bm25],
                similarity_top_k=5,
                num_queries=1,
                llm=self.llm
            )

        # 4. Plantilla de Prompt Estricta para el Sintetizador
        plantilla_QA = (
            "Actúa como un Consultor de Producto y Analista de Datos experto. Tu objetivo es responder la pregunta del usuario utilizando ÚNICAMENTE la información verídica y específica extraída de las reseñas proporcionadas en el contexto.\n"
            "---------------------\n"
            "CONTEXTO DE RESEÑAS INDEXADAS:\n"
            "{context_str}\n"
            "---------------------\n"
            "Normas estrictas de análisis:\n"
            "1. Si los datos recuperados mencionan problemas explícitos, anomalías o componentes faltantes (ej. ausencia de cables de carga, retrasos logísticos, fallas estéticas o de conectividad), enuméralos con precisión y fundamenta tu respuesta en la reseña correspondiente.\n"
            "2. Si la información recuperada no contiene datos suficientes para responder a la duda del cliente, responde textualmente de forma obligatoria: 'No se cuenta con registros suficientes en las opiniones indexadas para responder a esta consulta específica'. No asumas, no inventes historias de parejas ni metas datos de otros contextos.\n"
            "3. Mantén un tono técnico, objetivo, profesional y estructurado.\n\n"
            "Pregunta de análisis: {query_str}\n"
            "Respuesta:"
        )
        
        text_qa_template = PromptTemplate(plantilla_QA)

        # Configuración del motor usando el sintetizador con el prompt correcto
        sintetizador = CompactAndRefine(llm=self.llm, text_qa_template=text_qa_template)
        
        query_engine = RetrieverQueryEngine(
            retriever=fusion_retriever,
            response_synthesizer=sintetizador
        )

        # IMPORTANTE: Aquí mandamos la PREGUNTA LIMPIA, no el prompt entero.
        respuesta = query_engine.query(pregunta)
        return respuesta

if __name__ == "__main__":
    try:
        asistente = AsistenteAnaliticoHibrido()
    except Exception as e:
        print(f"[ERROR CRÍTICO] {e}")
        exit()

    print("\n" + "="*70)
    print("SISTEMA RAG DE ANALÍTICA DE PRODUCTO - ENTORNO HÍBRIDO LOCAL (Vectores + BM25)")
    print("="*70)
    print("Instrucciones: Introduzca consultas abiertas o utilice comandos de filtro.")
    print("Comandos disponibles:")
    print("  /interfaz   - Filtra exclusivamente análisis de Diseño e Interfaz")
    print("  /funcionalidad    - Filtra exclusivamente análisis de Funcionalidad")
    print("  /general  - Aísla únicamente quejas e inconformidades generales sin importar categoría")
    print("Para cerrar la sesión, escriba 'salir'.")
    print("="*70 + "\n")

    while True:
        entrada = input("Pregunta lo que quieras > ").strip()
        
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
            
        elif entrada.startswith("/funcionalidad"):
            cat_filtro = "Rendimiento y Caídas"
            pregunta_final = "Genera un reporte técnico enfocado en el rendimiento operativo, conectividad y fallas mecánicas/lógicas."
            print(f"[FILTRO APLICADO] Restringido a categoría: {cat_filtro}")
            
        elif entrada.startswith("/general"):
            sent_filtro = "General"
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