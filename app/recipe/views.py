"""
Vies for the recipe API.
"""
from rest_framework import (
    viewsets,
    mixins # Mixins can be "mixed in" to a view to add extra functionality
)
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import (
    Recipe,
    Tag,
    Ingredient
)
from recipe import serializers

from rest_framework.response import Response




# Create your views here.
# ModelViewSet is viewset to work with model
# Good for CRUD
# Will generate multiple endpoints
class RecipeViewSet(viewsets.ModelViewSet):
    """View for manage recipe APIs."""
    serializer_class = serializers.RecipeDetailSerializer
    # objects that are available for this viewset.
    # Because its a ModelViewSet it expects to work
    # with a model and to tell it which model to use you give it a query set
    queryset = Recipe.objects.all()
    # To be authenticated you must provide a token
    authentication_classes = [TokenAuthentication]
    # In order to use endpoints for this viewset you neeed to be authenticated
    permission_classes = [IsAuthenticated]

    # Out of the box this viewset would allow a user to manage all recipes (get_queryset would just return self.queryset which we defined above as being all recipes)
    # We want to limit them to manage only recipes they created by overwriting get_queryset
    def get_queryset(self):
        """Retrieve recipes for authenticated user."""
        # self.request.user is set by our authentication system we created.
        # We know this is defined because we said permission_classes to isauthenticated
        # which means to use this user must be authenticated so self.request.user will always be available.
        # If user is not authenticated a 401 will be thrown
        return self.queryset.filter(user=self.request.user).order_by('-id')

    # Method that gets called when DRF wants to determine the class for a particular action
    def get_serializer_class(self):
        """Return the serializer class for request"""
        if self.action == 'list':
            return serializers.RecipeSerializer
        return self.serializer_class

    # Override default create behavior of ModelViewSet
    # https://www.django-rest-framework.org/api-guide/generic-views/#get_serializer_classself
    # When we perform creation of new object through this view, we will call this method as part of that object creation
    # It takes the serializer which is the validated serializer (data has been validated)
    def perform_create(self, serializer):
        """Create a new recipe"""
        # Set user value to current authenticated user when model is saved to database.
        # Without this, there would be no user associated with recipe because by default
        # ModelViewSet simply creates the object with the details we provide and we did not provide the user
        # But the user exists in the request
        serializer.save(user=self.request.user)


class BaseRecipeAttrViewSet(mixins.DestroyModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet
                            ): # RecipeAttr refers to tags and ingredients
    """Base viewset for recipe attributes."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset to authenticated user."""
        return self.queryset.filter(user=self.request.user).order_by('-name')

# ListModelMixin allows you to add listing functionality for listing models
# GenericViewSet is a viewset that allows you to throw mixins in there so we can have viewset functionality that you desire for API

# This is because our API only need list capabilities, because tags and ingredients are added through the recipe endpoint
# and the tags/ingredients endpoints is only for retrieving a list for the user to select from..
# ModelViewSet provides the full CRUD endpoints, so it's overkill for this endpoint.

# If you look into the code for DRF, the ModelViewSet is actually doing the same thing we are, just with more base classes:

# https://github.com/encode/django-rest-framework/blob/master/rest_framework/viewsets.py#L239

class TagViewSet(BaseRecipeAttrViewSet):
    """Manage tags in the database."""
    serializer_class = serializers.TagSerializer
    queryset = Tag.objects.all()


class IngredientViewSet(BaseRecipeAttrViewSet):
    """Manage ingredients in the database"""
    serializer_class = serializers.IngredientSerializer
    # Tells view what is accessible to it. We later limit it on a user to user basis
    queryset = Ingredient.objects.all()


