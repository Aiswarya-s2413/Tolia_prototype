import threading
import time
from django.apps import AppConfig

def self_heal_vector_index():
    time.sleep(5)
    # Background embedding generation disabled to prevent Ollama model swapping and ensure 100% LLM responsiveness
    return

class ChatRagConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat_rag'

    def ready(self):
        # Launch background self-healing vector index worker on startup
        t = threading.Thread(target=self_heal_vector_index, daemon=True)
        t.start()
