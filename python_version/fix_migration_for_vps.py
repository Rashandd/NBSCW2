#!/usr/bin/env python
"""
Script to fix ChatMessage channel FK issue on VPS before running migration 0008.
Run this BEFORE migrating on VPS if you have existing ChatMessage records.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'python_version.settings')
django.setup()

from main.models import ChatMessage

# Set all existing ChatMessage channel fields to NULL
# This is safe because we made the field nullable
print("Setting all ChatMessage channel fields to NULL...")
count = ChatMessage.objects.all().update(channel=None)
print(f"Updated {count} ChatMessage records. You can now run migrations safely.")

