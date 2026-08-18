from rest_framework import serializers
from .models import Document, DocumentChunk, ChatLog, UserProfile

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'title', 'category', 'required_department', 'content', 'uploaded_at', 'is_confidential']

class ChatLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatLog
        fields = ['id', 'user_role', 'query', 'language', 'response', 'sources_used', 'access_blocked', 'created_at']
