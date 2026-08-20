from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField, HnswIndex

class Department(models.TextChoices):
    CEO = 'CEO', 'Chief Executive Officer (CEO)'
    QC = 'QC', 'Quality Control Inspector (QC)'

class DocumentCategory(models.TextChoices):
    GENERAL_SAFETY = 'GENERAL_SAFETY', 'General Plant Safety & Guidelines'
    BLAST_FURNACE = 'BLAST_FURNACE', 'Blast Furnace SOPs & Operations'
    MAINTENANCE = 'MAINTENANCE', 'Heavy Machinery Maintenance'
    QUALITY_CONTROL = 'QUALITY_CONTROL', 'Steel Quality & Testing SOPs'
    MARKETING_SALES = 'MARKETING_SALES', 'Confidential Marketing & Sales Data'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.CharField(
        max_length=50,
        choices=Department.choices,
        default=Department.CEO
    )

    def __str__(self):
        return f"{self.user.username} ({self.department})"

class Document(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=50,
        choices=DocumentCategory.choices,
        default=DocumentCategory.GENERAL_SAFETY
    )
    # The department required to view/retrieve this document via RAG
    required_department = models.CharField(
        max_length=50,
        choices=Department.choices,
        default=Department.QC,
        help_text="Minimum department required to access this document in RAG"
    )
    content = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_confidential = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.category}] {self.title} (Req: {self.required_department})"

class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField(default=0)
    text = models.TextField()
    embedding = VectorField(dimensions=768, null=True, blank=True)
    required_department = models.CharField(max_length=50, default=Department.QC)

    class Meta:
        indexes = [
            HnswIndex(
                name='chunk_embedding_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops']
            )
        ]

    def save(self, *args, **kwargs):
        # Automatic Vector Lifecycle Hook: Auto-embed chunk if missing embedding
        if not self.embedding and self.text:
            try:
                from .rag_engine import get_embedding
                vec = get_embedding(self.text)
                if vec:
                    self.embedding = vec
            except Exception as e:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.document.title} - Chunk #{self.chunk_index}"

class ChatLog(models.Model):
    user_role = models.CharField(max_length=50, default='FLOOR_WORKER')
    query = models.TextField()
    language = models.CharField(max_length=10, default='hi')  # 'hi' or 'en'
    response = models.TextField()
    sources_used = models.JSONField(default=list)
    access_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.user_role}][{self.language}] {self.query[:30]}..."
