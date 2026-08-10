from rest_framework import serializers
from .models import LSA_Profile, Skill

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']

class LSAProfileSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = LSA_Profile
        fields = ['id', 'full_name', 'email', 'skills', 'hourly_rate', 'is_active', 'created_at']

from .models import Booking, Parent
from django.db.models import Q

class BookingCreateSerializer(serializers.ModelSerializer):
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Parent.objects.all(), source='parent'
    )
    lsa_id = serializers.PrimaryKeyRelatedField(
        queryset=LSA_Profile.objects.all(), source='lsa'
    )

    class Meta:
        model = Booking
        fields = ['id', 'parent_id', 'lsa_id', 'start_time', 'end_time', 'status']
        read_only_fields = ['id', 'status']

    def validate(self, data):
        lsa = data.get('lsa')
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        if not lsa.is_active:
            raise serializers.ValidationError({"lsa_id": "This LSA is not currently active."})

        if start_time >= end_time:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})

        # Overlap check
        # An overlap occurs if a booking starts before the new booking ends AND ends after the new booking starts.
        overlapping_bookings = Booking.objects.filter(
            lsa=lsa,
            status__in=['pending', 'confirmed']
        ).filter(
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        if overlapping_bookings.exists():
            raise serializers.ValidationError(
                {"non_field_errors": "The selected time slot overlaps with an existing booking for this LSA."}
            )

        return data

class WebhookSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(choices=['payment.success', 'payment.failed'])
    provider_reference = serializers.CharField()
    booking_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
