import os
import uuid
import time
import requests
from typing import List, Dict, Any, Optional

class MemoryManager:
    """
    Manages semantic memory using ChromaDB.
    Supports both local embedded mode and remote server mode.
    """
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        if host and port:
            # Client-Server Mode (Production/Docker)
            # Add retry logic for initial connection (wait for Docker service to be READY)
            max_attempts = 15
            for attempt in range(max_attempts):
                try:
                    # Step 1: Raw HTTP heartbeat check
                    resp = requests.get(f"http://{host}:{port}/api/v1/heartbeat", timeout=5)
                    if resp.status_code == 200:
                        # Step 2: Instantiate client (imports inside to handle flaky lib states)
                        import chromadb
                        self.client = chromadb.HttpClient(host=host, port=port)
                        # Step 3: Verify tenant access
                        self.client.heartbeat()
                        print(f"[MemoryManager] Successfully connected to ChromaDB at {host}:{port}")
                        return
                    else:
                        print(f"[MemoryManager] ChromaDB returned status {resp.status_code}. Waiting...")
                except Exception as e:
                    print(f"[MemoryManager] ChromaDB connection attempt {attempt+1}/{max_attempts} failed: {e}")
                
                time.sleep(5)
            
            print(f"[MemoryManager] FAILED to connect to ChromaDB after {max_attempts} attempts.")
            # Fallback to local mode instead of crashing if possible? 
            # Or just raise to ensure the container restarts.
            raise RuntimeError("ChromaDB service unavailable")
        else:
            import chromadb
            # Persistent Local Mode (Development)
            persist_dir = os.path.join(os.getcwd(), "knowledge", "vector_db")
            os.makedirs(persist_dir, exist_ok=True)
            self.client = chromadb.PersistentClient(path=persist_dir)

    def get_or_create_collection(self, name: str):
        return self.client.get_or_create_collection(name=name)

    def add_memory(self, collection_name: str, content: str, metadata: Optional[Dict[str, Any]] = None, doc_id: Optional[str] = None):
        collection = self.get_or_create_collection(collection_name)
        id_to_use = doc_id or str(uuid.uuid4())
        collection.add(
            documents=[content],
            metadatas=[metadata or {}],
            ids=[id_to_use]
        )
        return id_to_use

    def search_memory(self, collection_name: str, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        collection = self.get_or_create_collection(collection_name)
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Flatten results
        formatted = []
        for i in range(len(results['ids'][0])):
            formatted.append({
                "id": results['ids'][0][i],
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i] if 'distances' in results else None
            })
        return formatted

    def get_memory_by_id(self, collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        collection = self.get_or_create_collection(collection_name)
        results = collection.get(ids=[doc_id])
        if results['ids']:
            return {
                "id": results['ids'][0],
                "content": results['documents'][0],
                "metadata": results['metadatas'][0]
            }
        return None

    def delete_memory(self, collection_name: str, doc_id: str):
        collection = self.get_or_create_collection(collection_name)
        collection.delete(ids=[doc_id])

# Global instance initialization helper
def init_memory_manager() -> MemoryManager:
    host = os.getenv("CHROMA_HOST")
    port = int(os.getenv("CHROMA_PORT", "8000")) if os.getenv("CHROMA_PORT") else None
    return MemoryManager(host=host, port=port)
