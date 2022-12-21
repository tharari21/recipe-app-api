"""
Vies for the recipe API.
"""
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)
from rest_framework import (
    viewsets,
    mixins, # Mixins can be "mixed in" to a view to add extra functionality
    status,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import (
    Recipe,
    Tag,
    Ingredient
)
from recipe import serializers

from rest_framework.response import Response


# extend schema for list endpoint to include filters
@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'tags',
                OpenApiTypes.STR,
                description='Comma separated list of tag IDs to filter'
            ),
            OpenApiParameter(
                'ingredients',
                OpenApiTypes.STR,
                description='Comma separated list of ingredient IDs to filter'
            ),
        ]
    )
)
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

    def _params_to_ints(self, qs):
        """Convert a list of strings to integers."""
        return [int(str_id) for str_id in qs.split(',')]

    # Out of the box this viewset would allow a user to manage all recipes (get_queryset would just return self.queryset which we defined above as being all recipes)
    # We want to limit them to manage only recipes they created by overwriting get_queryset
    def get_queryset(self):
        """Retrieve recipes for authenticated user."""
        # self.request.user is set by our authentication system we created.
        # We know this is defined because we said permission_classes to isauthenticated
        # which means to use this user must be authenticated so self.request.user will always be available.
        # If user is not authenticated a 401 will be thrown
        tags = self.request.query_params.get('tags')
        ingredients = self.request.query_params.get('ingredients')
        queryset = self.queryset

        if tags:
            tag_ids = self._params_to_ints(tags)
            # Filter on nested fields by using this __ notation
            queryset = queryset.filter(tags__id__in=tag_ids) # Check the id is in the tag_ids list
        if ingredients:
            ingredient_ids = self._params_to_ints(ingredients)
            queryset = queryset.filter(ingredients__id__in=ingredient_ids)

        # distinct() because we can get multiple results if a tag or ingredient is assigned to multiple recipes.
        return queryset.filter(
            user=self.request.user
        ).order_by('-id').distinct()

    # Method that gets called when DRF wants to determine the class for a particular action
    def get_serializer_class(self):
        """Return the serializer class for request"""
        if self.action == 'list':
            return serializers.RecipeSerializer
        # Custom action we will define - actions is how to add additional functionality on top of viewset
        # ModelViewSet consists of default actions such as list that we see above
        elif self.action == 'upload_image':
            return serializers.RecipeImageSerializer
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

    # add upload_image action that suppost POST method only.
    # detail=True makes action apply to detail portion of viewset - detail means it is a specific id of a recipe. The non detail view would be list view which has generic list of all recipes
    # We want this to apply to a recipe's detailed endpoint so a specific recipe ID must be provided
    # url_path is the custom url path for our action
    @action(methods=['POST'], detail=True, url_path='upload-image')
    def upload_image(self, request, pk=None):
        """Upload an image to recipe."""
        # Get recipe object using the primary key specified for the action i.e. the ID in the url
        recipe = self.get_object()
        # Indirectly calls get_serializer_class() to get the serializer instance of image. Since the action in this case is upload_image we get the RecipeImageSerializer
        serializer = self.get_serializer(recipe, data=request.data)

        # Check that serializer is valid
        if serializer.is_valid():
            # save the image to database
            serializer.save()
            # Return response with the image's data and 200 status code
            return Response(serializer.data, status=status.HTTP_200_OK)
        # Serializer was not valid so send back errors that serializer returned and 400
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'assigned_only',
                OpenApiTypes.INT, enum=[0,1],
                description='Filter by items assigned to recipes'
            )
        ]
    )
)
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
        assigned_only = bool(
            int(self.request.query_params.get('assigned_only', 0)) # If query param is not set then default to False
        )
        queryset = self.queryset
        if assigned_only:
            queryset = queryset.filter(recipe__isnull=False)

        return queryset.filter(
            user=self.request.user
        ).order_by('-name').distinct()

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


