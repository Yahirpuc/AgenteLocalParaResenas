import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from llama_index.core import StorageContext, VectorStoreIndex, Settings as LlamaSettings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core.schema import TextNode

# IMPORTACIONES NUEVAS PARA EL MOTOR HÍBRIDO
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.query_engine import RetrieverQueryEngine

from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import QueryEngineTool, ToolMetadata

class AsistenteAnaliticoHibrido:
    def __init__(self, ruta_db=os.path.join("datos", "base_vectorial"), nombre_coleccion="reviews_analizadas"):
        if not os.path.exists(ruta_db):
            raise FileNotFoundError(f"[ERROR] No se encontró la BD vectorial en '{ruta_db}'.")

        print("[INFO] Cargando modelos locales en memoria (Ollama)...")
        self.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
        self.llm = Ollama(model="qwen2.5:1.5b", request_timeout=300.0)

        LlamaSettings.llm = self.llm
        LlamaSettings.embed_model = self.embed_model

        print("[INFO] Estableciendo conexión asíncrona con ChromaDB...")
        self.db_cliente = chromadb.PersistentClient(
            path=ruta_db,
            settings=ChromaSettings(chroma_tenant="default_tenant", chroma_database="default_database", allow_reset=True)
        )
        self.chroma_collection = self.db_cliente.get_collection(name=nombre_coleccion)
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.index = VectorStoreIndex.from_vector_store(self.vector_store, storage_context=self.storage_context)
        
        # --- NUEVA LÓGICA DE FUSIÓN HÍBRIDA (BM25 + VECTORES) ---
        print("[INFO] Construyendo Nodos en memoria para BM25 (Solo en el arranque)...")
        datos_chroma = self.chroma_collection.get()
        nodos_memoria = [
            TextNode(text=texto, id_=id_doc, metadata=metadato) 
            for texto, id_doc, metadato in zip(datos_chroma['documents'], datos_chroma['ids'], datos_chroma['metadatas'])
        ]
        
        retriever_vectorial = self.index.as_retriever(similarity_top_k=5)
        retriever_bm25 = BM25Retriever.from_defaults(nodes=nodos_memoria, similarity_top_k=5)
        
        # Fusionamos ambos enfoques (Semántico + Léxico)
        fusion_retriever = QueryFusionRetriever(
            [retriever_vectorial, retriever_bm25],
            similarity_top_k=5,
            num_queries=1,
            llm=self.llm,
            mode="reciprocal_rerank"
        )
        
        # Construimos el Query Engine usando nuestro recuperador fusionado
        self.query_engine_rag = RetrieverQueryEngine.from_args(
            retriever=fusion_retriever,
            llm=self.llm
        )
        
        rag_tool = QueryEngineTool(
            query_engine=self.query_engine_rag,
            metadata=ToolMetadata(
                name="analizador_de_resenas",
                description=(
                    "HERRAMIENTA DE BÚSQUEDA. Úsala SOLO para buscar información en la base de datos sobre el producto. "
                    "REGLA VITAL: El argumento 'input' debe ser ÚNICAMENTE 1 o 2 palabras clave físicas (ej. 'batería', 'sonido', 'tornillos'). "
                    "REGLA DE RESUMEN: Si el usuario pide un resumen general, usa la palabra clave 'calidad' o 'producto'. "
                    "NUNCA pases preguntas completas, ni palabras abstractas como 'general', 'resumen' u 'opinión'."
                )
            )
        )
        self.herramientas_agente = [rag_tool]

    def iniciar_sesion_agente(self, historial_cargado=None):
        if historial_cargado is None:
            historial_cargado = []
            
        memoria_agente = ChatMemoryBuffer.from_defaults(chat_history=historial_cargado, token_limit=3000)
        
        # --- PROMPT DEFENSIVO INTEGRADO DE LA RAMA EXTERNA ---
        # --- PROMPT DEFENSIVO Y AUTÓNOMO OPTIMIZADO ---
        contexto_sistema = (
            "Eres un Analista Técnico Experto evaluando productos. Piensa, razona y responde SIEMPRE en Español.\n"
            "REGLA 1: Si el usuario te pregunta sobre algo que YA discutieron o te pide modificar una respuesta anterior (ej. traducir, resumir, comparar), usa ÚNICAMENTE tu memoria de la conversación. NO uses herramientas.\n"
            "REGLA 2: Usa la herramienta 'analizador_de_resenas' SOLO cuando el usuario pregunte por características, quejas o temas nuevos de los que aún no tienes contexto en la memoria.\n"
            "REGLA 3 (REGLA CRÍTICA DE FRONTERA): Si usas la herramienta y devuelve un resultado vacío o sin evidencia, responde EXACTAMENTE con esta frase: 'No se cuenta con registros suficientes en las opiniones indexadas para responder a esta consulta específica.'\n"
            "REGLA 4: Nunca inventes características que no existan en los datos recuperados."
        )

        agente = ReActAgent(
            tools=self.herramientas_agente,
            llm=self.llm,
            memory=memoria_agente,
            max_iterations=5,
            verbose=True,
            system_prompt=contexto_sistema
        )
        return agente