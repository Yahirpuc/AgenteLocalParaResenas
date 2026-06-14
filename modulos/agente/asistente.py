import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from llama_index.core import StorageContext, VectorStoreIndex, Settings as LlamaSettings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

# IMPORTACIONES MODERNAS Y LIMPIAS
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import QueryEngineTool, ToolMetadata

class AsistenteAnaliticoHibrido:
    def __init__(self, ruta_db=os.path.join("datos", "base_vectorial"), nombre_coleccion="reviews_analizadas"):
        """
        Inicializa el cerebro del agente. 
        Nota Arquitectónica: Hemos retirado la iteración síncrona en memoria de BM25 
        para evitar cuellos de botella de O(N). Todo el enrutamiento ahora confía 
        en la recuperación vectorial optimizada por ChromaDB.
        """
        if not os.path.exists(ruta_db):
            raise FileNotFoundError(f"[ERROR] No se encontró la BD vectorial en '{ruta_db}'.")

        print("[INFO] Cargando modelos locales en memoria (Ollama)...")
        
        # 1. Configuración de Modelos
        self.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
        
        # Forzamos a Ollama a no reservar 128k tokens en RAM
        self.llm = Ollama(
            model="qwen2.5:1.5b", 
            request_timeout=300.0
        )

        # 2. Configuración Global (Evita el bug de OpenAI)
        LlamaSettings.llm = self.llm
        LlamaSettings.embed_model = self.embed_model

        # 3. Conexión a Base de Datos Vectorial
        print("[INFO] Estableciendo conexión asíncrona con ChromaDB...")
        self.db_cliente = chromadb.PersistentClient(
            path=ruta_db,
            settings=ChromaSettings(
                chroma_tenant="default_tenant",
                chroma_database="default_database"
            )
        )
        self.chroma_collection = self.db_cliente.get_collection(name=nombre_coleccion)
        
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        self.index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            storage_context=self.storage_context
        )
        
        # 4. Creación de la Herramienta RAG (Query Engine)
        self.query_engine_rag = self.index.as_query_engine(similarity_top_k=5)
        
        rag_tool = QueryEngineTool(
            query_engine=self.query_engine_rag,
            metadata=ToolMetadata(
                name="analizador_de_resenas",
                description="HERRAMIENTA OBLIGATORIA. Úsala para leer las opiniones de los clientes. El argumento 'input' debe ser EXACTAMENTE el mismo tema, pregunta o palabra clave que el usuario te está solicitando."
            )
        )
        
        self.herramientas_agente = [rag_tool]

    def iniciar_sesion_agente(self, historial_cargado=None):
        """
        Instancia el Agente ReAct moderno.
        Cumple con el requerimiento de Sliding Window limitando los tokens.
        """
        if historial_cargado is None:
            historial_cargado = []
            
        memoria_agente = ChatMemoryBuffer.from_defaults(
            chat_history=historial_cargado,
            token_limit=3000 # Protege la VRAM local
        )
        
        contexto_sistema = (
            "Eres un Analista Técnico Experto. Tu única fuente de verdad es la base de datos local.\n"
            "REGLA 1: Para responder sobre el producto, usa SIEMPRE la herramienta 'analizador_de_resenas'.\n"
            "REGLA 2: Cuando uses la herramienta, el parámetro de búsqueda debe ser el tema exacto que pidió el usuario.\n"
            "REGLA 3: NUNCA inventes características que no estén en la base de datos.\n"
            "REGLA 4: Si el usuario te pide exportar, generar un reporte o guardar información, PRIMERO debes obtener esa información real usando tus herramientas de consulta, y LUEGO usar la herramienta de guardado pasando el texto completo extraído."
        )

        # Instanciación limpia y directa de LlamaIndex 0.13+
        agente = ReActAgent(
            tools=self.herramientas_agente,
            llm=self.llm,
            memory=memoria_agente,
            max_iterations=5,
            verbose=True,
            system_prompt=contexto_sistema
        )
        
        return agente