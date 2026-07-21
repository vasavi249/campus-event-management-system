import os
import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_event_manager.settings')
django.setup()

print("--- Step 1: Running Django Migrations ---")
call_command('makemigrations', 'events')
call_command('migrate')

print("--- Step 2: Seeding Initial Database Data ---")
from load_sample_data import populate
populate()

print("--- Step 3: Running Unit Tests ---")
call_command('test', 'events')
