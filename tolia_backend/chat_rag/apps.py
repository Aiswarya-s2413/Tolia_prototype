import threading
import time
from django.apps import AppConfig

def self_heal_vector_index():
    time.sleep(3) # Wait for DB and server to settle
    try:
        from .models import DocumentChunk
        from .rag_engine import get_embedding
        missing_chunks = DocumentChunk.objects.filter(embedding__isnull=True)
        count = missing_chunks.count()
        if count > 0:
            print(f"[Vector Index Self-Healing] Found {count} unindexed chunks. Generating embeddings...")
            for chunk in missing_chunks:
                vec = get_embedding(chunk.text)
                if vec:
                    chunk.embedding = vec
                    chunk.save(update_fields=['embedding'])
            print("[Vector Index Self-Healing] All chunks successfully vector indexed!")
    except Exception as e:
        pass

class ChatRagConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat_rag'

    def ready(self):
        # Launch background self-healing vector index worker on startup
        t = threading.Thread(target=self_heal_vector_index, daemon=True)
        t.start()
