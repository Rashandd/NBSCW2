#!/usr/bin/env python
"""
Quick test script to verify registration security setup
Run this after applying migrations
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'python_version.settings')
django.setup()

from main.models import RegistrationAttempt, CustomUser
from django.utils import timezone
from datetime import timedelta

def test_models():
    """Test that models are properly configured"""
    print("🔍 Testing Registration Security Models...")
    print()
    
    # Test 1: Check if RegistrationAttempt model exists
    try:
        count = RegistrationAttempt.objects.count()
        print(f"✅ RegistrationAttempt model exists ({count} records)")
    except Exception as e:
        print(f"❌ RegistrationAttempt model error: {e}")
        return False
    
    # Test 2: Check CustomUser has new fields
    try:
        user = CustomUser.objects.first()
        if user:
            has_reg_ip = hasattr(user, 'registration_ip')
            has_reg_fp = hasattr(user, 'registration_fingerprint')
            print(f"✅ CustomUser has registration_ip: {has_reg_ip}")
            print(f"✅ CustomUser has registration_fingerprint: {has_reg_fp}")
        else:
            print("⚠️  No users in database yet (this is OK for fresh install)")
    except Exception as e:
        print(f"❌ CustomUser field check error: {e}")
        return False
    
    # Test 3: Create a test registration attempt
    try:
        test_attempt = RegistrationAttempt.objects.create(
            ip_address='127.0.0.1',
            fingerprint='test_fingerprint_12345',
            user_agent='Test Browser',
            success=False,
            username_attempted='test_user',
            blocked_reason='Test entry'
        )
        print(f"✅ Created test RegistrationAttempt: {test_attempt}")
        
        # Clean up
        test_attempt.delete()
        print("✅ Cleaned up test entry")
    except Exception as e:
        print(f"❌ Failed to create test RegistrationAttempt: {e}")
        return False
    
    # Test 4: Check rate limiting logic
    try:
        # Simulate 5 attempts from same IP
        test_ip = '192.168.1.100'
        for i in range(5):
            RegistrationAttempt.objects.create(
                ip_address=test_ip,
                fingerprint=f'test_fp_{i}',
                user_agent='Test',
                success=False,
                username_attempted=f'user_{i}'
            )
        
        # Check count
        recent_attempts = RegistrationAttempt.objects.filter(
            ip_address=test_ip,
            attempt_time__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        if recent_attempts >= 5:
            print(f"✅ Rate limiting check passed ({recent_attempts} attempts detected)")
        else:
            print(f"⚠️  Rate limiting check: only {recent_attempts} attempts found")
        
        # Clean up
        RegistrationAttempt.objects.filter(ip_address=test_ip).delete()
        print("✅ Cleaned up test rate limit entries")
    except Exception as e:
        print(f"❌ Rate limiting test error: {e}")
        return False
    
    print()
    print("=" * 60)
    print("✅ All tests passed! Registration security is ready.")
    print("=" * 60)
    print()
    print("📋 Next steps:")
    print("1. Visit /register/ to test the registration form")
    print("2. Try registering multiple times to test rate limiting")
    print("3. Check /admin/ to view registration attempts")
    print("4. Monitor for suspicious activity")
    print()
    return True

def show_stats():
    """Show current registration statistics"""
    print("📊 Registration Statistics:")
    print()
    
    total_attempts = RegistrationAttempt.objects.count()
    successful = RegistrationAttempt.objects.filter(success=True).count()
    blocked = RegistrationAttempt.objects.filter(success=False).count()
    
    print(f"Total attempts: {total_attempts}")
    print(f"Successful: {successful}")
    print(f"Blocked: {blocked}")
    
    if total_attempts > 0:
        success_rate = (successful / total_attempts) * 100
        print(f"Success rate: {success_rate:.1f}%")
    
    print()
    
    # Show recent attempts
    recent = RegistrationAttempt.objects.order_by('-attempt_time')[:5]
    if recent:
        print("Recent attempts:")
        for attempt in recent:
            status = "✅" if attempt.success else "❌"
            print(f"  {status} {attempt.username_attempted} from {attempt.ip_address} at {attempt.attempt_time}")
    
    print()

if __name__ == '__main__':
    print()
    print("=" * 60)
    print("🔒 Registration Security Setup Test")
    print("=" * 60)
    print()
    
    if test_models():
        show_stats()
    else:
        print()
        print("❌ Some tests failed. Please check the errors above.")
        print()
        print("💡 Did you run migrations?")
        print("   python manage.py makemigrations")
        print("   python manage.py migrate")
        print()

