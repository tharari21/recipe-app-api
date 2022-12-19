"""
Serializers for the user API view
"""
from django.contrib.auth import (
    get_user_model,
    authenticate
)
from django.utils.translation import gettext as _
from rest_framework import serializers

# Serializers take json input, validates input (based on how we configure validation)
# then converts to a python object that we can use or a model in our actual database (what we're doing here)
# ModelSerializer allows us to automatically validate and save to the database
class UserSerializer(serializers.ModelSerializer):
    """Serializer for the user object"""

    # Tell rest_framework which model we are using, what fields we are accepting and any additional arguments we should pass to serializer
    class Meta:
        # Tells is to use the User model
        model = get_user_model()
        # List of fields available through the serializer - just things that need to be created or set when you make a request
        # Will only allow these fields so in this case API cannot change is_active, is_staff or is_superuser
        fields = ['email', 'password', 'name']
        # Provide extra metadata to different fields - basically validations
        # Write only makes it so that the password can be set and updated but never read - for security
        # min_length is a validation option. If password is less than 5 chars, get a 400 bad request
        extra_kwargs = {'password': {'write_only': True, 'min_length': 5}}

    # Override the behavior the serializer does when you create new objects from serializer.
    # Default behavior for create is to create an object with whatever values are passed in. So for instance if we didnt override create,
    # the serializer would take the password and store it in the User database without hashing it which is not what we want. Instead we'd
    # prefer the create_user method be called to create user
    # This method will be called after the valiudation and will only be called if validation was successful.
    def create(self, validated_data):
        """Create and return a new user with encrypted password given the validated data."""
        # Anytime we create user from user model this will be called
        return get_user_model().objects.create_user(**validated_data)

    # instance = user model instance that is being updated
    # validated_data = data that user sent that has passed through serializer validation - in this case email,password, and name
    def update(self, instance, validated_data):
        """Update and return user"""
        # Anytime we perform update on user model this will be called
        # Retrieve password from validated data and remove it from validated_data
        password = validated_data.pop('password', None) # Default value of none if it's not there (in the case that user only wants to update email or name not password then password won't be there)
        # Calls the base serializer class' update method. This performs existing updating steps provided by base class
        # We're only overriding and changing what we need to change so we don't have to rewrite the code in parent method
        # Note that we removed password from validated data so this won't update the password. This will be handled by us
        user = super().update(instance, validated_data)

        if password: # If user specified a password then call set_password to hash password and set it for the user
            user.set_password(password)
            user.save()
        # Expected behavior of update is to return user so that the view that calls it can get the updated user back
        return user

class AuthTokenSerializer(serializers.Serializer):
    """Serializer for user auth token"""
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False # by default drf will trim whitespace for char field so we don't want that
    )

    # Inherited from Serializer class and Called during validation stage of serialization
    # So when data is posted to view, it will be passed to serializer which will call validate to validate that data is correct
    def validate(self, attrs):
        """Validate and authenticate the user."""
        email = attrs.get('email')
        password = attrs.get('password')
        # authenticate is built into django
        # Accepts request context the user sent - not sure why they need that but not important - to get request in serializer we call self.context.get('request')
        # If user is authenticated then it will return the user otherwise none
        user = authenticate(
            request=self.context.get('request'), #
            username=email,
            password=password
        )
        # If not authenticated
        if not user:
            msg = _("Unable to authenticate with provided credentials")
            # Standard way to raise error with serializers. The view will translate this raised error
            # to an HTTP bad request and will send the message
            raise serializers.ValidationError(msg, code='authorization')

        # Set user attribute so we can user 'user' in the view that calls this
        attrs['user'] = user
        # Return attributes
        return attrs