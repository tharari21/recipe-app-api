"""
Django command to wait for database to be available.
"""
import time

from psycopg2 import OperationalError as Psycopg2Error # Potential error thrown by psycopg2 when db is not ready

from django.db.utils import OperationalError # Another potential error django throws when database is not ready. Django can either raise this or psycopg2 error
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    """Django command to wait for database"""

    # Whenever we run wait_for_db command, it will call this method
    def handle(self, *args, **options):
        """Entrypoint for command."""
        # Log message to screen waiting for database
        self.stdout.write("Waiting for database...")
        # assume db is not up
        db_up = False # boolean to see if db is running
        while not db_up:
            try:
                # check is a method that checks entire django project for potential problems. By passing databases we are checking specifically if databases have problems
                self.check(databases=['default']) # method we patch in tests
                db_up = True
            except (Psycopg2Error,OperationalError):
                self.stdout.write("Database unavailable, waiting 1 second...")
                time.sleep(1)
        # style.SUCCESS makes it green for success
        self.stdout.write(self.style.SUCCESS("Database available!"))
        
