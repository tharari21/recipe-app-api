"""
Tests for the tags API
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag

from recipe.serializers import TagSerializer


TAG_URL = reverse('recipe:tag-list')

# We could reuse the create_user method from other test modules but sometimes we want custom logic to be applied
def create_user(email='user@example.com', password='testpass123'):
    """Create and return a new user"""
    return get_user_model().objects.create_user(email=email, password=password)

class PublicTagsAPITest(TestCase):
    """Test unauthenticated API requests."""
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required for retrieving tags."""
        res = self.client.get(TAG_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateTagsAPITest(TestCase):
    """Test authenticated API requests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags"""
        Tag.objects.create(user=self.user, name="Vegan")
        Tag.objects.create(user=self.user, name="Dessert")

        res = self.client.get(TAG_URL)

        # We use order_by so that the result is consistent
        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to authenticated user."""
        other_user = create_user(email='other@example.com',)
        Tag.objects.create(user=other_user, name='Fruity')
        tag = Tag.objects.create(user=self.user, name='Comfort Food')

        res = self.client.get(TAG_URL)


        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # in recipe tests when testing if recipes were limited to user we used a different method
        # This is to show that there are different ways to test it and just because its different
        # Does not mean it's wrong
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)