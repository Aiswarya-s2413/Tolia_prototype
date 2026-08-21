from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Document, DocumentChunk, ChatLog, Department, DocumentCategory
from .serializers import DocumentSerializer, ChatLogSerializer
from .rag_engine import LocalRAGEngine

class ChatAPIView(APIView):
    def post(self, request):
        query = request.data.get('query', '').strip()
        user_role = request.data.get('user_role', Department.CEO)
        target_lang = request.data.get('language', None)

        if not query:
            return Response({'error': 'Query text is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Execute RAG query with RBAC security filter
        rag_result = LocalRAGEngine.query(user_query=query, user_role=user_role, target_lang=target_lang)

        # Save query log to database
        chat_log = ChatLog.objects.create(
            user_role=user_role,
            query=query,
            language=rag_result['language'],
            response=rag_result['response'],
            sources_used=rag_result['sources'],
            access_blocked=rag_result['access_blocked']
        )

        return Response({
            'id': chat_log.id,
            'query': query,
            'user_role': user_role,
            'language': rag_result['language'],
            'response': rag_result['response'],
            'sources': rag_result['sources'],
            'access_blocked': rag_result['access_blocked'],
            'timestamp': chat_log.created_at
        })

class DocumentListCreateView(APIView):
    def get(self, request):
        user_role = request.query_params.get('role', Department.CEO)
        if user_role == Department.CEO:
            docs = Document.objects.all().order_by('-uploaded_at')
        else: # QC
            docs = Document.objects.filter(required_department=Department.QC).order_by('-uploaded_at')
            
        serializer = DocumentSerializer(docs, many=True)
        return Response(serializer.data)

    def post(self, request):
        title = request.data.get('title')
        category = request.data.get('category', DocumentCategory.GENERAL_SAFETY)
        required_department = request.data.get('required_department', Department.QC)
        content = request.data.get('content')
        is_confidential = request.data.get('is_confidential', False)

        if not title or not content:
            return Response({'error': 'Title and content are required'}, status=status.HTTP_400_BAD_REQUEST)

        doc = Document.objects.create(
            title=title,
            category=category,
            required_department=required_department,
            content=content,
            is_confidential=is_confidential
        )

        # Chunking & Vector Embedding Generation (150 words per chunk)
        words = content.split()
        chunk_size = 150
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i+chunk_size])
            chunk_vector = LocalRAGEngine.get_embedding(chunk_text)
            DocumentChunk.objects.create(
                document=doc,
                chunk_index=i // chunk_size,
                text=chunk_text,
                embedding=chunk_vector,
                required_department=required_department
            )

        serializer = DocumentSerializer(doc)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class UserRoleView(APIView):
    def get(self, request):
        roles = [
            {
                'code': Department.CEO,
                'name': 'Chief Executive Officer (CEO)',
                'description': 'Full unrestricted access across all plant documents, reports & sales targets.',
                'can_access_sales': True
            },
            {
                'code': Department.QC,
                'name': 'Quality Control Inspector (QC)',
                'description': 'Access to Quality Control, Safety & Operational SOPs. Restricted from confidential sales data.',
                'can_access_sales': False
            }
        ]
        return Response(roles)

class SeedDataView(APIView):
    def post(self, request):
        """Clear all existing documents and chat logs from the local database."""
        deleted_docs = Document.objects.all().delete()[0]
        deleted_chunks = DocumentChunk.objects.all().delete()[0]
        ChatLog.objects.all().delete()

        return Response({
            'message': f'Successfully cleared database. Removed {deleted_docs} documents and {deleted_chunks} chunks.',
            'count': 0
        })

class VoiceTranscribeView(APIView):
    """Local Speech-to-Text (STT) endpoint using faster-whisper / local Indic speech models."""
    def post(self, request):
        audio_file = request.FILES.get('audio')
        language = request.data.get('language', 'en')
        
        if not audio_file:
            return Response({'error': 'Audio file is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        from .voice_service import LocalSTTService
        audio_bytes = audio_file.read()
        result = LocalSTTService.transcribe_audio(audio_bytes, language=language)
        
        if result.get('success'):
            return Response({
                'text': result['text'],
                'language': result.get('language', language)
            })
        else:
            return Response({'error': result.get('error', 'Transcription failed')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.http import HttpResponse

class VoiceSynthesizeView(APIView):
    """Local Text-to-Speech (TTS) endpoint returning WAV audio stream."""
    def get(self, request):
        text = request.query_params.get('text', '').strip()
        language = request.query_params.get('lang', 'en')
        return self._generate_audio(text, language)

    def post(self, request):
        text = request.data.get('text', '').strip()
        language = request.data.get('lang', 'en')
        return self._generate_audio(text, language)

    def _generate_audio(self, text, language):
        if not text:
            return HttpResponse(b"", content_type="audio/wav", status=400)
        from .voice_service import LocalTTSService
        wav_bytes = LocalTTSService.synthesize_speech(text, language=language)
        if wav_bytes:
            response = HttpResponse(wav_bytes, content_type="audio/wav")
            response['Content-Length'] = len(wav_bytes)
            response['Accept-Ranges'] = 'bytes'
            return response
        return HttpResponse(b"", content_type="audio/wav", status=500)


