from django.urls import path
from .views import ChatAPIView, DocumentListCreateView, UserRoleView, SeedDataView

urlpatterns = [
    path('chat/', ChatAPIView.as_view(), name='api_chat'),
    path('documents/', DocumentListCreateView.as_view(), name='api_documents'),
    path('roles/', UserRoleView.as_view(), name='api_roles'),
    path('seed/', SeedDataView.as_view(), name='api_seed'),
]
