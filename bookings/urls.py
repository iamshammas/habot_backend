from django.urls import path
from .views import LSAProfileSearchView, BookingCreateView

urlpatterns = [
    path('lsas/search/', LSAProfileSearchView.as_view(), name='lsa-search'),
    path('bookings/', BookingCreateView.as_view(), name='booking-create'),
]
