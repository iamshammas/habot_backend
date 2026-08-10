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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Payment, Booking
from .serializers import WebhookSerializer
import logging

logger = logging.getLogger(__name__)

class PaymentWebhookView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = WebhookSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Webhook malformed payload: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        provider_ref = data['provider_reference']
        booking_id = data['booking_id']
        event_type = data['event_type']

        with transaction.atomic():
            # Idempotency check: if a payment with this provider_ref already exists and has a final status
            if Payment.objects.filter(provider_reference=provider_ref).exists():
                logger.info(f"Webhook ignored: Duplicate provider_reference {provider_ref}")
                return Response({"detail": "Already processed"}, status=status.HTTP_200_OK)

            try:
                booking = Booking.objects.select_for_update().get(id=booking_id)
            except Booking.DoesNotExist:
                logger.error(f"Webhook failed: Unknown booking {booking_id}")
                return Response({"detail": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

            payment_status = 'success' if event_type == 'payment.success' else 'failed'
            
            # Create or update the Payment record
            payment, created = Payment.objects.get_or_create(
                booking=booking,
                defaults={
                    'amount': data['amount'],
                    'status': payment_status,
                    'provider_reference': provider_ref
                }
            )
            if not created:
                payment.status = payment_status
                payment.provider_reference = provider_ref
                payment.save()

            # Transition Booking state
            if event_type == 'payment.success':
                booking.status = 'confirmed'
            else:
                booking.status = 'cancelled'
            booking.save()

            logger.info(f"Webhook processed: Booking {booking.id} is now {booking.status}")

        return Response({"detail": "Processed"}, status=status.HTTP_200_OK)

