from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import LSA_Profile, Skill

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
        url = reverse('lsa-search')
        
        # Without prefetch_related, this would be 1 (LSA query) + 10 (skill queries per LSA) + 1 (count for pagination) = 12 queries.
        # With prefetch_related, this should be 1 (count) + 1 (LSA query) + 1 (prefetch skills) = 3 queries.
        with self.assertNumQueries(3):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data['results']), 10)

