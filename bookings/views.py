from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from django.db.models import Prefetch
from .models import LSA_Profile, Skill
from .serializers import LSAProfileSerializer

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class LSAProfileSearchView(generics.ListAPIView):
    serializer_class = LSAProfileSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        # We start by ensuring we only get active LSAs, and we prefetch the skills
        # to avoid the N+1 query problem.
        queryset = LSA_Profile.objects.filter(is_active=True).prefetch_related('skills').order_by('-created_at')

        skills_param = self.request.query_params.get('skills', None)
        if skills_param:
            skill_names = [s.strip() for s in skills_param.split(',')]
            # Filter LSAs that have ANY of the requested skills
            queryset = queryset.filter(skills__name__in=skill_names).distinct()

        return queryset

from .serializers import BookingCreateSerializer

class BookingCreateView(generics.CreateAPIView):
    serializer_class = BookingCreateSerializer
    # status field defaults to 'pending' as defined in the model, and it's read-only in serializer.

