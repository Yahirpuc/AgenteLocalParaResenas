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
        self.chroma_collection = self.db_cliente.get_or_create_collection(name=nombre_coleccion)
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.index = VectorStoreIndex.from_vector_store(self.vector_store, storage_context=self.storage_context)
        
        # --- NUEVA LÓGICA DE FUSIÓN HÍBRIDA (BM25 + VECTORES) ---
        print("[INFO] Construyendo Nodos en memoria para BM25 (Solo en el arranque)...")
        datos_chroma = self.chroma_collection.get()
        
        nodos_memoria = [
            TextNode(text=texto, id_=id_doc, metadata=metadato) 
            for texto, id_doc, metadato in zip(datos_chroma.get('documents', []), datos_chroma.get('ids', []), datos_chroma.get('metadatas', []))
        ]
        
        retriever_vectorial = self.index.as_retriever(similarity_top_k=5)
        
        # Validamos si hay nodos antes de crear el BM25
        if nodos_memoria:
            retriever_bm25 = BM25Retriever.from_defaults(nodes=nodos_memoria, similarity_top_k=5)
            lista_retrievers = [retriever_vectorial, retriever_bm25]
            print("[INFO] Motor Híbrido: Vectorial + BM25 activados.")
        else:
            print("[WARN] Colección vacía. BM25 inactivo temporalmente. Iniciando solo con vectorial.")
            lista_retrievers = [retriever_vectorial]
        
        # Fusionamos los enfoques dinámicamente según lo que esté disponible
        fusion_retriever = QueryFusionRetriever(
            lista_retrievers,
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
                    "CRITICAL SEARCH TOOL. Úsala para buscar ABSOLUTAMENTE TODO lo relacionado con los productos: "
                    "opiniones, quejas, fallas de hardware, durabilidad, rendimiento técnico, estado del empaque, "
                    "logística de envío, problemas de entrega, satisfacción general o cualquier detalle mencionado en las reseñas.\n"
                    "ORDEN DE ENRUTAMIENTO GENÉRICO: Si te estoy saludando, haciendo charla casual, preguntando quién eres "
                    "o pidiéndote tareas sobre el texto que ya tienes en pantalla, NO uses esta herramienta; "
                    "responde directamente usando tu memoria de forma inmediata.\n"
                    "BLINDAJE ANTI-ALUCINACIÓN: Si la herramienta no devuelve registros válidos o retorna texto vacío, "
                    "debes decirme textualmente: 'No cuento con registros suficientes para esa consulta.' "
                    "Está estrictamente prohibido inventar características o asumir datos que no estén escritos.\n"
                    "REGLA DE IDIOMA Y TRATO DIRECTO: Háblame SIEMPRE en español de forma directa a mí ('Tú / Usted'). "
                    "Queda totalmente prohibido usar el inglés o responder con frases explicativas en tercera persona como "
                    "'para que el usuario analice' o 'el usuario solicita'. Contéstame a mí de forma concisa.\n"
                    "REGLA DE ARGUMENTO: El parámetro 'input' debe ser obligatoriamente una o dos palabras clave atómicas "
                    "y en minúsculas (ej. 'batería', 'empaque', 'envío', 'calidad')."
                )
            )
        )
        self.herramientas_agente = [rag_tool]

    def iniciar_sesion_agente(self, historial_cargado=None):
        if historial_cargado is None:
            historial_cargado = []
            
        memoria_agente = ChatMemoryBuffer.from_defaults(chat_history=historial_cargado, token_limit=3000)
        
        # --- PROMPT DEFENSIVO, AUTÓNOMO Y DE CORRECCIÓN DE CONDUCTA ---
      # --- PROMPT DEFENSIVO, DE CONDUCTA Y CONTROL DE RESPUESTA FINAL ---
        contexto_sistema = (
            "Eres el Analista Técnico Experto oficial de Ordevs Soluciones. Piensa, razona y responde SIEMPRE en Español.\n\n"
            "REGLA MÁXIMA DE COMPORTAMIENTO Y CONDUCTA:\n"
            "- Debes mantener una postura estrictamente respetuosa, educada y profesional ante CUALQUIER situación.\n"
            "- Si se presentan groserías, insultos, lenguaje vulgar o provocativo, ignora la ofensa por completo "
            "y responde de forma cortés indicando que eres un asistente profesional enfocado en el análisis técnico.\n"
            "- Tienes terminantemente prohibido usar groserías, lenguaje inapropiado, palabras ofensivas o sarcasmo.\n\n"
            "REGLAS OBLIGATORIAS DE RESPUESTA DIRECTA (ANTI-ALUCINACIÓN):\n"
            "- Habla DIRECTAMENTE conmigo ('Tú / Usted'). Está TERMINANTEMENTE PROHIBIDO usar frases explicativas en tercera persona "
            "o responder dándome órdenes a mí o al sistema (ejemplo: NO digas 'por favor investiga la pregunta' ni 'verifique si hay información').\n"
            "- Tu trabajo es redactar la conclusión directamente basada en lo que leíste de la herramienta.\n\n"
            "REGLAS ESTRUCTURALES DEL FLUJO:\n"
            "REGLA 1: Si el usuario te pregunta sobre algo que YA discutieron o te pide modificar una respuesta anterior (ej. traducir, resumir, comparar), usa ÚNICAMENTE tu memoria de la conversación. NO uses herramientas.\n"
            "REGLA 2: Usa la herramienta 'analizador_de_resenas' SOLO cuando el usuario pregunte por características, quejas o temas nuevos de los que aún no tienes contexto en la memoria.\n"
            "REGLA 3 (REGLA CRÍTICA DE FRONTERA): Si usas la herramienta y devuelve un resultado vacío o sin evidencia, responde EXACTAMENTE con esta frase: 'No se cuenta con registros suficientes en las opiniones indexadas para responder a esta consulta específica.'\n"
            "REGLA 4: Nunca inventes características que no existan en los datos recuperados."
        )

        agente = ReActAgent(
            tools=self.herramientas_agente,
            llm=self.llm,
            memory=memoria_agente,
            max_iterations=2,
            verbose=True,
            system_prompt=contexto_sistema      
        )
        return agente