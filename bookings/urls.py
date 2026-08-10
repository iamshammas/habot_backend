from django.urls import path
from .views import LSAProfileSearchView

urlpatterns = [
    path('lsas/search/', LSAProfileSearchView.as_view(), name='lsa-search'),
]
