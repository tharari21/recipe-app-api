"""
Tests for recipe API.
"""
from decimal import Decimal

import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag,
    Ingredient
)
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)
RECIPES_URL = reverse('recipe:recipe-list')

# Generate a url for a given recipe_id
def detail_url(recipe_id):
    """Create and return a recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])

def image_upload_url(recipe_id):
    """Create and return image upload URL."""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])

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

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags."""
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [
                {
                    'name': 'Thai'
                },
                {
                    'name': 'Dinner'
                }
            ]
        }
        res = self.client.post(RECIPES_URL, payload, format='json') # since we have nested data we want to ensure it converts to json

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        # Make sure we have 1 recipe for the user so on the next line we don't get a generic IndexError thrown instead we'd see that count of recipes is not 1
        # So not including this will be fine but more information will be provided if we assert this
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tag."""
        tag_indian = Tag.objects.create(user=self.user, name='Indian')

        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            'price': Decimal('4.50'),
            # We'd expect only Breakfast tag to be created
            'tags': [
                {
                    'name': 'Indian'
                },
                {
                    'name': 'Breakfast'
                }
            ]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all()) # Ensure that the specific tag we created above exists in recipe and not a different one with a new ID
        for tag in payload['tags']:
            exists = Tag.objects.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating a new tag when updating a recipe with tags that don't exist."""
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertTrue(res.status_code, status.HTTP_200_OK)
        # Get the tag created with the patch request and ensure that it's assigned to recipe
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe"""
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        # Lunch already exists so this should not create a new tag
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test clearing recipe's tags."""
        tag = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Test creating a new recipe containing new ingredients creates new ingredients in the database"""

        payload = {
            'title': 'Cauliflower Tacos',
            'time_minutes': 60,
            'price': Decimal('4.30'),
            'ingredients': [{'name': 'Cauliflower'}, {'name': 'Salt'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating a new recipe with existing ingredients does not create new ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Lemon')

        payload = {
            'title': 'Vietnamese Soup',
            'time_minutes': '25',
            'price': Decimal('2.55'),
            'ingredients': [{'name': 'Lemon'}, {'name': 'Fish Sauce'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertTrue(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        # Check that the post with an existing ingredient did not create a new ingredient
        self.assertEqual(recipe.ingredients.count(), 2)
        # Check that the specific Lemon ingredient created above is the same one used in the recipe
        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']
            ).exists()
            self.assertTrue(exists)
    def test_create_ingredient_on_update(self):
        """Test creating new ingredient when updating a recipe."""

        recipe = create_recipe(user=self.user)

        payload = {
            'ingredients': [{'name': 'Limes'}]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='Limes')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an existing ingredient on update of recipe."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Pepper')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name='Chili')
        payload = {
            'ingredients': [{'name': 'Chili'}]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipe's ingredients."""
        ingredient = Ingredient.objects.create(user=self.user, name='Garlic')
        recipe = create_recipe(self.user)
        recipe.ingredients.add(ingredient)

        payload = {
            'ingredients': []
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        # Called when each test is finished
        # We do this because we don't want to be building test images on our machine everytime we run tests
        # If we didnt do this, each time we test which will be a lot in development, we will have saved the images.
        # We want to clean up at the end of testing
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading images."""
        # Get upload image url
        url = image_upload_url(self.recipe.id)
        # Create a named temporary file. This file will be created locally and removed after this block ends
        # image_file is the reference to the file
        # two image files - first is file user uploads - image user has on machine,
        # then there will be a new image file which is the stored version of the user's file on the server
        # We create the user uploaded file using PIL Image object below
        # The RGB (10,10) creates a 10x10 black square

        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            # Creates image in RAM but not saved to a file
            img = Image.new('RGB', (10,10))
            # save image to the temporary image file
            img.save(image_file, format='JPEG')
            # Seek back to beginning of file because img.save moves the cursor to end of file
            image_file.seek(0)
            # Payload to upload to API. Format is multipart because we upload it as a multipart form - best way to upload images using rest_framework.
            # need a multipartform and this payload simulates a multipart form
            payload = {'image': image_file}
            # multipart contains text and binary data (the image)
            res = self.client.post(url, payload, format='multipart')

        # Refresh recipe so it now has image that we uploaded with API
        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Check that image is in the response
        self.assertIn('image', res.data)
        # Check that the file path of the recipe's image exists
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_image_bad_request(self):
        """Test uploading invalid image."""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
