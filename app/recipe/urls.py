"""
URL mapping for the recipe app
"""
from django.urls import (
    path,
    include
)
from rest_framework.routers import DefaultRouter
from recipe import views

# Sets up urls for us using the view
router = DefaultRouter()
# Assigns endpoints from RecipeViewSet to /recipes
# RecipeViewSet enables all methods for CRUD - GET,POST,PUT,PATCH,DELETE
router.register('recipes', views.RecipeViewSet)
router.register('tags', views.TagViewSet)
router.register('ingredients', views.IngredientViewSet)

# name for reverse lookups of urls
app_name = 'recipe'

urlpatterns = [
    # urls generated automatically from router
    path('', include(router.urls)),
]