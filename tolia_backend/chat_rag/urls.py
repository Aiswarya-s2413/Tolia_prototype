from django.urls import path
from .views import ChatAPIView, DocumentListCreateView, UserRoleView, SeedDataView, VoiceTranscribeView, VoiceSynthesizeView

urlpatterns = [
    path('chat/', ChatAPIView.as_view(), name='api_chat'),
    path('documents/', DocumentListCreateView.as_view(), name='api_documents'),
    path('roles/', UserRoleView.as_view(), name='api_roles'),
    path('seed/', SeedDataView.as_view(), name='api_seed'),
    path('voice/transcribe/', VoiceTranscribeView.as_view(), name='api_voice_transcribe'),
    path('voice/synthesize/', VoiceSynthesizeView.as_view(), name='api_voice_synthesize'),
]

