from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from .models import LSA_Profile, Skill, Parent, Booking, Payment

class LSAProfileSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.skill_math = Skill.objects.create(name="Math")
        self.skill_science = Skill.objects.create(name="Science")
        
        # Create 10 LSAs
        for i in range(10):
            lsa = LSA_Profile.objects.create(
                full_name=f"LSA {i}",
                email=f"lsa{i}@example.com",
                hourly_rate=20.00,
                is_active=True
            )
            lsa.skills.add(self.skill_math, self.skill_science)

    def test_search_query_count_is_flat(self):
        # Test 1: LSA Search (success, flat query count).
        url = reverse('lsa-search')
        
        with self.assertNumQueries(3):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 10)


class BookingAndPaymentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.parent = Parent.objects.create(
            full_name="John Doe",
            email="john@example.com",
            phone="1234567890"
        )
        self.lsa = LSA_Profile.objects.create(
            full_name="Jane Smith",
            email="jane@example.com",
            hourly_rate=25.00,
            is_active=True
        )
        self.booking_url = reverse('booking-create')
        self.webhook_url = reverse('payment-webhook')

    def test_booking_creation_success(self):
        # Test 2: Booking creation (success).
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        payload = {
            "parent_id": self.parent.id,
            "lsa_id": self.lsa.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        response = self.client.post(self.booking_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')
        self.assertTrue(Booking.objects.filter(id=response.data['id']).exists())

    def test_booking_overlap_validation_failure(self):
        # Test 3: Booking overlap validation (failure).
        start_time = timezone.now() + timedelta(days=2)
        end_time = start_time + timedelta(hours=2)
        
        # Create existing booking
        Booking.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            start_time=start_time,
            end_time=end_time,
            status='pending'
        )
        
        # Attempt overlapping booking
        payload = {
            "parent_id": self.parent.id,
            "lsa_id": self.lsa.id,
            "start_time": (start_time + timedelta(hours=1)).isoformat(), # Overlaps
            "end_time": (end_time + timedelta(hours=1)).isoformat()
        }
        
        response = self.client.post(self.booking_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_webhook_idempotency_success(self):
        # Test 4: Webhook idempotency (success, duplicate ignored).
        start_time = timezone.now() + timedelta(days=3)
        end_time = start_time + timedelta(hours=1)
        
        booking = Booking.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            start_time=start_time,
            end_time=end_time,
            status='pending'
        )
        
        payload = {
            "event_type": "payment.success",
            "provider_reference": "uniq-ref-123",
            "booking_id": booking.id,
            "amount": "25.00"
        }
        
        # First call
        response1 = self.client.post(self.webhook_url, payload, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')
        self.assertEqual(Payment.objects.count(), 1)
        
        # Second call (idempotent)
        response2 = self.client.post(self.webhook_url, payload, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data['detail'], "Already processed")
        self.assertEqual(Payment.objects.count(), 1)

    def test_webhook_payment_failed(self):
        # Test 5: Webhook payment failed (success, booking cancelled).
        start_time = timezone.now() + timedelta(days=4)
        end_time = start_time + timedelta(hours=1)
        
        booking = Booking.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            start_time=start_time,
            end_time=end_time,
            status='pending'
        )
        
        payload = {
            "event_type": "payment.failed",
            "provider_reference": "uniq-ref-456",
            "booking_id": booking.id,
            "amount": "25.00"
        }
        
        response = self.client.post(self.webhook_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')
        
        payment = Payment.objects.get(booking=booking)
        self.assertEqual(payment.status, 'failed')

