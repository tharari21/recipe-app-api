"""
Tests for models
"""
from unittest.mock import patch # tool to use to mock things
from decimal import Decimal
from django.test import TestCase
# Get default user model for project.
# We can reference model directly
# but this way is best practice so
# if you change User model we don't need to modify code
from django.contrib.auth import get_user_model
from core import models

def create_user(email='user@example.com', password='testpass123'):
    """Create and return a new user."""
    return get_user_model().objects.create_user(email, password)

class ModelTests(TestCase):
    """Test models."""

    def test_create_user_with_email_successful(self):
        """Test creating a user with email is successful"""
        # Reserved domain name for testing -
        # use example.com for testing always
        email = "test@example.com"
        password = "testpass123"
        # objects is a reference to the manager we will create.
        # Recall that django provides a default manager that we can override
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )
        self.assertEqual(user.email, email)
        # Checks that password is correct by using check_password (provided by default model manager)
        # This will check that hashed password is equal to the password of the created user
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self, ):
        """Test email is normalized for new users."""
        sample_emails = [
            ["test1@EXAMPLE.com", "test1@example.com"],
            ["Test2@Example.com", "Test2@example.com"],
            ["TEST3@EXAMPLE.com", "TEST3@example.com"],
            ["test4@example.COM", "test4@example.com"]
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, "sample123")
            self.assertEqual(user.email, expected)
    def test_new_user_without_email_raises_error(self):
        """Test that creating a user without an email raises a ValueError"""
        # Checks that the block inside raises ValueError
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user("", "sample123")

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = get_user_model().objects.create_superuser(
            "test@example.com",
            "sample123"
        )

        self.assertTrue(user.is_superuser) # Field provided by PermissionsMixin - allows access to everything inside django admin
        self.assertTrue(user.is_staff) # Field defined by us - allows user to log into django admin

    def test_create_recipe(self):
        """Test creating a recipe is successful"""
        # need a user to create a recipe
        user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        recipe = models.Recipe.objects.create(
            user=user, # user that created the recipe
            title='Sample Recipe Name',
            time_minutes=5,
            price=Decimal('5.50'), # Not using float because Decimal is more accurate
            description='Sample recipe description.'
        )

        # Our model will have a stringify method that makes it the title
        self.assertEqual(str(recipe), recipe.title)

    def test_create_tag(self):
        """Test creating a tag is successful"""
        user = create_user()
        tag = models.Tag.objects.create(user=user, name='Tag1')

        self.assertEqual(str(tag), tag.name)

    def test_create_ingredient(self):
        """Test creating an ingredient is successful"""
        user = create_user()
        ingredient = models.Ingredient.objects.create(user=user, name='Lettuce')

        self.assertEqual(str(ingredient), ingredient.name)

    # We want to mock this uuid function that we will actually use for testing purposes
    # The reason we do this is to replace behavior of uuid.
    # We don't want to create an actual uuid for testing purposes because then we can't identify it.
    @patch('core.models.uuid.uuid4')
    def test_recipe_file_name_uuid(self, mock_uuid):
        """Test generating image path."""
        # We will use the uuid for the image in the  file name
        uuid = 'test-uuid'
        # now the function call to generate uuid will be replaced to return test-uuid string
        mock_uuid.return_value = uuid
        # We will add this function which generates the file path to the image being uploaded
        # None is supposed to be the recipe instance we are uploading to but for testing purposes none is fine and then the file name
        file_path = models.recipe_image_file_path(None, 'example.jpg')

        # Check that the file_path returned is equal to expected file name
        self.assertEqual(file_path, f'uploads/recipe/{uuid}.jpg')