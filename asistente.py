import os
import asyncio
import sys
import chromadb
from chromadb.config import Settings
from llama_index.core import StorageContext, VectorStoreIndex 
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.retrievers.bm25 import BM25Retriever

from llama_index.storage.chat_store.sqlite import SQLiteChatStore
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import CondenseQuestionChatEngine 


class AsistenteAnaliticoHibrido:
    def __init__(self, ruta_db="chroma_db", nombre_coleccion="reviews_analizadas"):
        if not os.path.exists(ruta_db):
            raise FileNotFoundError(f"[ERROR] No se encontró el almacenamiento persistente en '{ruta_db}'. Ejecute 'main.py' con la opción de extracción primero.")

        print("[INFO] Cargando modelos locales en memoria (Ollama)...")
        self.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
        self.llm = Ollama(model="qwen2.5:1.5b", request_timeout=120.0)

        print("[INFO] Estableciendo conexión con ChromaDB...")
        self.db_cliente = chromadb.PersistentClient(
            path=ruta_db,
            settings=Settings(
                chroma_tenant="default_tenant",
                chroma_database="default_database",
                allow_reset=True
            )
        )
        self.chroma_collection = self.db_cliente.get_collection(name=nombre_coleccion)
        
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        self.index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            storage_context=self.storage_context,
            embed_model=self.embed_model
        )
        
        print("[INFO] Recuperando documentos de ChromaDB para el motor de palabras clave (BM25)...")
        from llama_index.core.schema import TextNode
        
        datos_chroma = self.chroma_collection.get()
        self.nodos_documentos = []
        
        for texto, id_doc, metadato in zip(datos_chroma['documents'], datos_chroma['ids'], datos_chroma['metadatas']):
            self.nodos_documentos.append(
                TextNode(text=texto, id_=id_doc, metadata=metadato)
            )
        print(f"[INFO] Éxito: {len(self.nodos_documentos)} nodos cargados en el motor BM25.")

        self.chat_store = SQLiteChatStore.from_uri(uri="sqlite:///sesiones_chat.sqlite")
        self.memory = None 

    def cerrar_conexion(self):
        print("[INFO] Vaciando registros internos de la base de datos de forma segura...")
        try:
            todos_los_datos = self.chroma_collection.get()
            if todos_los_datos and todos_los_datos['ids']:
                self.chroma_collection.delete(ids=todos_los_datos['ids'])
                print("[INFO] Colección de ChromaDB vaciada con éxito.")
            else:
                print("[INFO] La base de datos ya estaba limpia.")
        except Exception as e:
            print(f"[ADVERTENCIA] No se pudo vaciar la colección internamente: {e}")

    def iniciar_sesion(self, conversation_id: str):
        self.memory = ChatMemoryBuffer.from_defaults(
            token_limit=3000, 
            chat_store=self.chat_store, 
            chat_store_key=conversation_id
        )
        print(f"[INFO] Memoria persistente cargada/creada para la sesión: {conversation_id}")

    async def consultar(self, pregunta: str, filtro_categoria: str = None, filtro_sentimiento: str = None):
        if not self.memory:
            raise ValueError("[ERROR] Debes llamar a 'iniciar_sesion()' antes de realizar consultas.")

        from llama_index.core.response_synthesizers import CompactAndRefine
        from llama_index.core import PromptTemplate
        from llama_index.core.llms import ChatMessage, MessageRole

        # ── Filtros de metadatos ──
        lista_filtros = []
        if filtro_categoria:
            lista_filtros.append(ExactMatchFilter(key="categoria", value=filtro_categoria))
        if filtro_sentimiento:
            lista_filtros.append(ExactMatchFilter(key="sentimiento", value=filtro_sentimiento))
        filtros = MetadataFilters(filters=lista_filtros) if lista_filtros else None

        # ── Recuperadores ──
        retriever_vectorial = self.index.as_retriever(similarity_top_k=5, filters=filtros)
        
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
        
        top_k_dinamico = min(5, len(nodos_filtrados)) if nodos_filtrados else 5

        if not nodos_filtrados:
            retriever_bm25 = retriever_vectorial
        else:
            retriever_bm25 = BM25Retriever.from_defaults(nodes=nodos_filtrados, similarity_top_k=top_k_dinamico)
        
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

        # ── Prompt ──
        plantilla_QA = (
            "<|im_start|>system\n"
            "Actúa como un Consultor de Producto y Analista Técnico experto. Tu única tarea es responder la consulta del usuario utilizando ÚNICAMENTE el contexto de reseñas provisto. "
            "Sé directo, frío, objetivo y estructurado en tu análisis. No asumas, no extrapoles ni inventes características o quejas que no estén escritas textualmente.\n"
            "REGLA DE ORO HÍBRIDA: Préstale especial atención tanto al contexto general de las opiniones como a los términos o palabras clave exactas que el usuario está buscando.\n"
            "REGLA CRÍTICA DE FRONTERA: Si el contexto está vacío, no contiene datos suficientes o no responde directamente a la pregunta, debes contestar EXACTAMENTE con esta frase, sin añadir nada más:\n"
            "'No se cuenta con registros suficientes en las opiniones indexadas para responder a esta consulta específica.'\n"
            "CONTEXTO DE RESEÑAS:\n{context_str}<|im_end|>\n"
            "<|im_start|>user\n"
            "Pregunta de análisis: {query_str}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        text_qa_template = PromptTemplate(plantilla_QA)
        sintetizador = CompactAndRefine(llm=self.llm, text_qa_template=text_qa_template)
        query_engine = RetrieverQueryEngine(
            retriever=fusion_retriever,
            response_synthesizer=sintetizador
        )

        # ── a) Historial ──
        historial_mensajes = self.memory.get()
        historial_str = ""
        for msg in historial_mensajes:
            historial_str += f"{msg.role.value.capitalize()}: {msg.content}\n"

        # ── b) Condensación (síncrona via hilo dedicado) ──
        pregunta_condensada = pregunta
        if historial_str.strip():
            print("[INFO] Evaluando contexto del historial...")
            prompt_condensacion = (
                "Tu tarea es reescribir la pregunta del usuario para que se entienda por sí sola, "
                "utilizando el contexto del historial SOLO si la pregunta hace referencia indirecta a él (ej. 'este', 'el producto', 'resúmelo'). "
                "REGLA CRÍTICA: Si la pregunta del usuario introduce un tema, objeto o producto completamente diferente (ej. zapatos, tenis, carros, etc.) "
                "que NO tiene relación con el historial, DEBES dejar la pregunta exactamente igual, sin modificarla.\n\n"
                f"Historial de conversación:\n{historial_str}\n"
                f"Pregunta original: {pregunta}\n"
                "Pregunta final a buscar:"
            )
            respuesta_llm = await self.llm.acomplete(prompt_condensacion)
            pregunta_condensada = respuesta_llm.text.strip()
            print(f"[RAG] Pregunta ajustada al contexto: {pregunta_condensada}")

        # ── c) Búsqueda RAG Híbrida ──
        respuesta = await query_engine.aquery(pregunta_condensada)

        # ── d) Guardar en memoria ──
        self.memory.put(ChatMessage(role=MessageRole.USER, content=pregunta))
        self.memory.put(ChatMessage(role=MessageRole.ASSISTANT, content=respuesta.response))

        return respuesta.response


if __name__ == "__main__":
    try:
        asistente = AsistenteAnaliticoHibrido()
        print("[OK] Módulo de asistencia híbrida listo para producción.")
    except Exception as e:
        print(f"[STATUS] Esperando inicialización base desde el orquestador central: {e}")