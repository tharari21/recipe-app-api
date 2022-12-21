"""
Serializers for recipe API.
"""
from rest_framework import serializers
from core.models import (
    Recipe,
    Tag,
    Ingredient
)



class TagSerializer(serializers.ModelSerializer):
    """Serializer for tags."""
    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']

class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for ingredients."""

    class Meta:
        model = Ingredient
        fields = ['id', 'name']
        read_only_fields = ['id']

class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for recipes."""
    tags = TagSerializer(many=True, required=False)
    ingredients = IngredientSerializer(many=True, required=False)

    class Meta:
        model = Recipe
        fields = ['id', 'title', 'time_minutes', 'price', 'link', 'tags', 'ingredients']
        read_only_fields = ['id'] # So user can't change database ID of recipe

    def _get_or_create_tags(self, tags: Tag, recipe: Recipe):
        """Handle getting or creating tags as needed"""
        auth_user = self.context['request'].user # Get authenticated user
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(
                user=auth_user,
                # Important to use ** instead of manually passing tag['name'] because if we add fields later we'd have to modify this code. This way we don't need to do that
                **tag
            )
            recipe.tags.add(tag_obj)

    # _ before means internal method - only to be called inside of class
    def _get_or_create_ingredients(self, ingredients: list[Ingredient], recipe: Recipe):
        """Handle getting or creating ingredients as needed"""
        auth_user = self.context['request'].user
        for ingredient in ingredients:
            ingredient_obj, created = Ingredient.objects.get_or_create(
                user=auth_user,
                **ingredient)
            recipe.ingredients.add(ingredient_obj)

    def create(self, validated_data):
        """Create a recipe."""
        tags = validated_data.pop('tags', []) # Remove tags from validated data. If tags isnt there get an empty list
        ingredients = validated_data.pop('ingredients', [])

        # Create recipe object without the tags - if we passed the tags it would not work because it expects tags to be added as a related field separately
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags, recipe)
        self._get_or_create_ingredients(ingredients, recipe)

        # create method must return the object it created
        return recipe

    # Instance is the instance we are updating
    def update(self, instance: Recipe, validated_data):
        """Update a recipe."""
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        # ingredients = validated_data.pop('ingredients', None)
        if tags is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags, instance)

        if ingredients is not None:
            instance.ingredients.clear()
            self._get_or_create_ingredients(ingredients, instance)

        # All other attributes other than tags i.e. title, price, time_minutes, etc. is assigned to instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # Save updated changes to recipe
        instance.save()
        return instance



# Detail serializer is simply an extention so RecipeSerializer
class RecipeDetailSerializer(RecipeSerializer):
    """Serializer for recipe detail view"""

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']


# Separate serializer for image uploads
# Needs a separate serializer because when we
# upload images we only need to accept image field
# and not the other recipe fields
# The reason it's a separate API for images is because it's best practice to only upload one type of data to an API
# So we don't want to upload form data as well as an image
# We want a specific API just for image uploads
class RecipeImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading images to recipes."""

    class Meta:
        model = Recipe
        fields = ['id', 'image']
        read_only_fields = ['id']
        extra_kwargs = {'image': {'required': 'True'}}