"""
Views for the user API
"""
# Base class to configure for views that handles requests in a standardized way
# While giving us the ability to override some of that behavior
from rest_framework import generics, authentication, permissions
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings



from user.serializers import (
    UserSerializer,
    AuthTokenSerializer
)

# Class based view - handles post requests used to create resource
# generics.CreateAPIView handles everything for us all we do is pass
# the serializer class so rest_framework know which model we want to
# use and how to serialize it
class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system."""
    serializer_class = UserSerializer

# ObtainAuthToken is a base view provided by rest_framework
# We give it our AuthTokenSerializer to tell it that when validating we want an email field not username
# By default it uses username not email to authenticate
class CreateTokenView(ObtainAuthToken):
    """Create a new auth token for user"""
    serializer_class = AuthTokenSerializer
    # optional - uses default renderer classes - makes it available in the browsable API in our docs
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

# RetrieveUpdateAPIView is provided by rest_framework and provides functionality needed for retrieving (GET) and updating (PATCH/PUT) objects in DB
# Does not allow POST requests
class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user."""
    serializer_class = UserSerializer
    # authentication = how do you know the user is who they say they are so for that we are using TokenAuthentication
    # permissions = know who the user is but what can they do? We want the user that uses this API to be authenticated that's all then they can do what they want
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    # Overrides the base class - gets the object for the HTTP get request
    # The way authentication system works is when user is authenticated, the user object that is authenticated
    # gets assigned to the request object that's availablew in the view
    # We can get the attached user once authenticated from this method
    # So when user makes a GET to /me, the associated view method which is defined in the base class
    # will call this overrriden get_object and then run it through UserSerializer then return result to API
    def get_object(self):
        """Retrieve and return the authenticated user"""
        return self.request.user