"""
Test custom Django management commands
"""


# Mocking behavior of database since we need to simulate database returning a response
from unittest.mock import patch

# Potential error we might get when connecting to DB before it's ready
from psycopg2 import OperationalError as Psycopg2Error

# Helper function by django to call management command by name
from django.core.management import call_command
# Another exception that may be thrown by database
from django.db.utils import OperationalError
# Base test class for testing
from django.test import SimpleTestCase

@patch("core.management.commands.wait_for_db.Command.check") # This is the command that we will be mocking. The .Command.check is provided by the BaseCommand which is what the wait_for_db.py file class inherits from.
class CommandTests(SimpleTestCase):
    """Test commands."""
    def test_wait_for_db_ready(self, patched_check): # Because we gave patch decorator, all methods in this class get patched_check parameter
        """Test waiting for database if database ready."""
        # When check is called inside our command, we want it to simply return true
        patched_check.return_value = True
        
        call_command("wait_for_db")

        # ensures core.management.commands.wait_for_db.Command.check is called with the parameter database=['default']
        patched_check.assert_called_once_with(databases=['default'])
        
    # Don't want to sleep during tests
    @patch("time.sleep")
    def test_wait_for_db_delay(self, patched_sleep, patched_check):
        """Test waiting for database when getting OperationalError"""
        # Raise exception instead of actually returning a value, use side_effect. 
        # Pass it items that acts based on what we pass so if we pass exception, the mocking library knows to raise it. 
        # We're saying for the first 2 times raise Psycopg2Error, then we raise 3 operational errors then return true
        # This is to simulate starting the database so for the first 2 times it returns Psycopg2 error then we get a general 
        # OperationalError 3 times then the db is ready so return true
        patched_check.side_effect = [Psycopg2Error] * 2 + \
            [OperationalError] * 3 + [True]
        
        call_command('wait_for_db')
        # We called patched check 6 times (twice Psycopg2 error, 3 OperationalErrors and one true)
        self.assertEqual(patched_check.call_count, 6)
         # Check it was called with default database
        patched_check.assert_called_with(databases=['default'])