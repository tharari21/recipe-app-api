"""
Tests for the Django admin modifications.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status

class AdminSiteTests(TestCase):
    """Tests for Django admin."""
    # SetUp method to setup modules at the beginning of each test in our class
    def setUp(self):
        """Create client, superuser to authenticate client with and then a regular test user."""
        # django test client to make http requests
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="testpass123"
        )

        self.client.force_login(self.admin_user)
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="testpass123",
            name="Test User"
        )

    def test_users_list(self):
        """Test that uses our listed on page"""
        # get url for changelist. This is sort of a variable
        # that is predefined in official documentation of django
        # Basically link to page that displays list of users
        url = reverse("admin:core_user_changelist")
        # Request is made authenticated as the superuser we created.
        res = self.client.get(url)

        # Check that page contains name of user created and email address
        self.assertContains(res, self.user.name)
        self.assertContains(res, self.user.email)

    def test_edit_user_page(self):
        """Test the edit user page works"""
        # URL for change user page and
        # we pass id of user we want to change
        url = reverse("admin:core_user_change", args=[self.user.id])

        res = self.client.get(url)

        # Check that page loads. That's all we need to know
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_user_page(self):
        """Test the create user page."""
        url = reverse("admin:core_user_add")

        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)