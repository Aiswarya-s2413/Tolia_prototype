import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tolia_backend.settings')
django.setup()

from chat_rag.models import Document, DocumentChunk
from chat_rag.rag_engine import get_embedding

def embed_all_chunks():
    chunks = DocumentChunk.objects.filter(embedding__isnull=True)
    print(f"Generating embeddings for {chunks.count()} chunks...")
    for chunk in chunks:
        vec = get_embedding(chunk.text)
        if vec:
            chunk.embedding = vec
            chunk.save(update_fields=['embedding'])
            print(f"Embedded chunk #{chunk.chunk_index} of {chunk.document.title}")
        else:
            print(f"Failed embedding for {chunk.document.title}")
    print("All chunks embedded successfully!")

if __name__ == "__main__":
    embed_all_chunks()
