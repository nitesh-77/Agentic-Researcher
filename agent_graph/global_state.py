import os
from typing import List
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_mistralai import MistralAIEmbeddings

class GlobalState:
    """Singleton for managing ChromaDB vector store across the session"""

    _instance = None
    _vectorstore = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalState, cls).__new__(cls)
            cls._instance._initialize_vectorstore()
        return cls._instance

    def _initialize_vectorstore(self):
        """Initialize ChromaDB with Mistral embeddings"""
        if self._vectorstore is None:
            try:
                embeddings = MistralAIEmbeddings(
                    model="mistral-embed",
                    mistral_api_key=os.getenv("MISTRAL_API_KEY")
                )
                self._vectorstore = Chroma(
                    embedding_function=embeddings,
                    collection_name="research_docs"
                )
            except Exception as e:
                print(f"⚠️ Vector store init failed (Safe Fail): {e}")
                self._vectorstore = None

    def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to vector store"""
        if not documents:
            return False
            
        if self._vectorstore is None:
            self._initialize_vectorstore()

        if self._vectorstore:
            try:
                self._vectorstore.add_documents(documents)
                print(f"✅ Added {len(documents)} documents to DB")
                return True
            except Exception as e:
                print(f"❌ Error adding docs: {e}")
                return False
        return False

    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """Perform similarity search safely"""
        if self._vectorstore is None:
            self._initialize_vectorstore()
        
        if self._vectorstore is None:
            return []

        try:
            # GUARD: Check if collection is empty to prevent crash
            if hasattr(self._vectorstore, '_collection') and self._vectorstore._collection.count() == 0:
                print("⚠️ DB is empty, skipping search")
                return []

            results = self._vectorstore.similarity_search(query, k=k)
            return results
        except Exception as e:
            print(f"⚠️ Search failed gracefully: {e}")
            return []

    def clear_vectorstore(self):
        """Clear all documents safely"""
        if self._vectorstore:
            try:
                self._vectorstore.delete_collection()
                # Re-init immediately
                self._vectorstore = None
                self._initialize_vectorstore()
                print("🗑️ Vector store cleared")
            except Exception as e:
                print(f"⚠️ Error clearing DB (Ignored): {e}")

    def get_document_count(self) -> int:
        """Get number of documents in vector store safely"""
        if self._vectorstore is None:
            return 0
        try:
            # Safe access to private collection for counting
            if hasattr(self._vectorstore, '_collection'):
                return self._vectorstore._collection.count()
            return 0
        except:
            return 0


    @property
    def is_initialized(self) -> bool:
        """Check if vector store is properly initialized"""
        return self._vectorstore is not None

# Global singleton instance
def get_global_state() -> GlobalState:
    return GlobalState()

def cleanup_global_state():
    instance = GlobalState._instance
    if instance is not None:
        instance.clear_vectorstore()