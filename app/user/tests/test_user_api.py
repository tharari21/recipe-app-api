"""
Tests for the user api
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create') # URL path for creating a user
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')

# instead of calling the get_user_model() everytime
def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)

# Public tests - don't require authentication
class PublicUserAPITests(TestCase):
    """Test the public features of the user API."""
    # Gets called before each test
    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating a user is successful"""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name'
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        # Make sure user will never get back hashed password
        self.assertNotIn('password', res.data) # Ensures there's no key called password in res.data
    def test_user_with_email_exists_error(self):
        """Test error returned if user with email exists."""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name'
        }

        # Create user then try creating another user to ensure that it fails
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def password_too_short_error(self):
        """Test an error is returned if password is less than 5 characters."""
        payload = {
            'email': 'test@example.com',
            'password': 'pw',
            'name': 'Test Name'
        }
        res = self.client.get(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # Confirm that user was not created with short password
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test for generating user token for valid credentials"""
        user_details = {
            'name': 'Test Name',
            'email': 'test@example.com',
            'password': 'test-user-123',
        }
        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': user_details['password']
        }
        res = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """Test returns error if creadentials are invalid"""
        payload = {
            'email': 'test@example.com',
            'password': 'badpass'
        }
        # user does not exist
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """Test posting a blank password returns an error"""
        payload = {
            'email': 'test@example.com',
            'password': ''
        }

        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """Test authentication is required for users."""
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


# Private tests - require authentication
# The reason we separate public and private is because we are going to
# authenticate in the setUp method in this class but the other one we don't
class PrivateUserAPITests(TestCase):
    """Test API requests that require authentication."""
    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            password='testpass123',
            name="Test User"
        )

        self.client = APIClient()
        # Force authenticate user - do this so we don't have to actually authenticate
        # Now every request we make for this client will be authenticated
        # We are not testing if token url works here we simply want to authenticate user
        # so subsequenet requests have access to endpoints. For this reason we did not
        # send a request to generate a token
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """Test retrieving profile for logged in user"""
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'email': self.user.email,
            'name': self.user.name
        })
    def test_post_me_not_allowed(self):
        """Test POST is not allowed for /me endpoint"""
        # POST should not be allowed for /me because we are not creating a /me resource
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """Test updating the user profile for the authenticated user"""
        payload = {
            'name': 'Updated Name',
            'password': 'newpassword123'
        }
        res = self.client.patch(ME_URL, payload)

        # Make sure user values are refreshed. The values of the instance are loaded when we created the user
        # But if data is changed in DB then this does not change until we call refresh
        self.user.refresh_from_db() # create_user() returns model instance so this method is available
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

