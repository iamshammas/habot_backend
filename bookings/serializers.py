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
