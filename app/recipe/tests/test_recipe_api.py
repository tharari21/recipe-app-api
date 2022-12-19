"""
Tests for recipe API.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)
RECIPES_URL = reverse('recipe:recipe-list')

# Generate a url for a given recipe_id
def detail_url(recipe_id):
    """Create and return a recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])


# Helper function to create recipe
def create_recipe(user, **params):
    """Create and return sample recipe"""
    # We don't want to have to pass in all this each time create recipe is called so we provide defaults for whatever is not passed
    defaults = {
        'title': 'Sample Recipe Title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf'
    }
    # If params are passed it will overwrite any defined in defaults otherwise will use defaults
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe

def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)

class PublicRecipeAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateRecipeAPITests(TestCase):
    """Test authenticated API REQUESTS."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')

        # We're not testing authentication so no need to authenticate using APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes."""
        create_recipe(self.user)
        create_recipe(self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id') # Expect them to be returned in descending id order
        # Expect result to match what the serializer returns so we pass that to serializer.
        # We want to make sure the expected data equals data from res
        serializer = RecipeSerializer(recipes, many=True) # many=True bc serializers can either return one item or list of items. many=True tells it we're getting a list
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    # We tested that it retrieves a list of recipes but now we need to check that it returns a list of recipes that belong to the user who is authenticated
    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated user."""
        other_user = create_user(email='other@example.com',password='otherpass123')
        create_recipe(other_user)
        create_recipe(self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user) # Only returns one item so order_by is not necessary
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_details(self):
        """Test get recipe detail"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating new recipe"""
        payload =  {
            'title': 'Sample Recipe Title',
            'time_minutes': 30,
            'price': Decimal('5.99'),
        }
        # Create recipe
        res = self.client.post(RECIPES_URL, payload)
        # Check successfully created
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Retrieve the recipe we created. We know resource was created so this can't fail
        recipe = Recipe.objects.get(id=res.data['id'])

        # For each payload key value pair check that the key in the recipe object from database equals the value from payload.
        # Basically check that the recipe created was created with all the info we created with
        for k,v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        # Check that the recipe's user is the user that we forced authentication with
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update of recipe."""
        # Since we're testing a partial update we want to ensure other fields that are not present in payload are unchanged
        original_link = "https://example.com/recipe.pdf"
        recipe = create_recipe(
            user=self.user,
            title='Sample Recipe',
            link=original_link,
        )
        payload = {
            'title': 'New Recipe Title'
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update of recipe."""
        recipe = create_recipe(
            user=self.user,
            title='Sample Recipe',
            link='https://example.com/recipe.pdf',
            description='Sample description'
        )
        payload = {
            'title': 'New Title',
            'link': 'https://example.com/new-recipe.pdf',
            'description': 'New description',
            'time_minutes': 10,
            'price': Decimal('2.50')
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test updating recipe's user results in an error"""
        new_user = create_user(
            email='test@example.com',
            password='testpass123'
        )
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe successfully."""

        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT) # Standard status code for delete
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_users_recipe_error(self):
        """Test trying to delete other user's recipe returns error"""
        new_user = create_user(
            email='other@example.com',
            password='testpass123'
        )
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        # The current user is self.user so should not be able to delete other user's recipe
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        # Make sure it still exists
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())