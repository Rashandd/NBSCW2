"""
Security utilities for registration and bot detection
"""
import re
import hashlib
import time
from typing import List, Tuple, Optional
from django.core.cache import cache
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ProfanityFilter:
    """
    Profanity filter for username and display name validation.
    Uses a combination of exact match and pattern detection.
    """
    
    # Common profanity words in multiple languages (extensible list)
    PROFANITY_LIST = {
        # English
        'fuck', 'shit', 'bitch', 'asshole', 'bastard', 'dick', 'cock', 'pussy',
        'whore', 'slut', 'cunt', 'nigger', 'faggot', 'retard',
        # Turkish
        'sik', 'amk', 'orospu', 'piç', 'göt', 'yarrak', 'amına', 'sikeyim',
        'oç', 'pezevenk', 'kaltak', 'ibne', 'puşt',
        # Spanish
        'puta', 'mierda', 'pendejo', 'cabron', 'joder', 'coño',
        # German
        'scheiße', 'ficken', 'hurensohn', 'arschloch',
        # French
        'merde', 'putain', 'salaud', 'connard', 'enculé',
    }
    
    # Patterns that commonly appear in offensive usernames
    OFFENSIVE_PATTERNS = [
        r'n+[i1!]+g+[ge3]+[ra@]+',  # Racial slur patterns
        r'f+[ua@]+[ck]+',            # F-word variations
        r'sh+[i1!]+t+',              # S-word variations
        r'b+[i1!]+t+ch+',            # B-word variations
        r'k+[i1!]+l+l+',             # Violence references
        r'd+[i1!]+e+',               # Death references
        r'h+[a@]+t+[e3]+',           # Hate references
    ]
    
    # Known bot/spam indicators in usernames
    BOT_PATTERNS = [
        r'bot\d*$',
        r'^bot_',
        r'spam',
        r'admin\d*$',
        r'support\d*$',
        r'moderator\d*$',
        r'^test\d+$',
    ]
    
    @classmethod
    def contains_profanity(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text contains profanity.
        Returns (has_profanity, matched_word_or_pattern)
        """
        if not text:
            return False, None
        
        text_lower = text.lower()
        
        # Replace common letter substitutions
        normalized = cls._normalize_leetspeak(text_lower)
        
        # Check exact matches
        for word in cls.PROFANITY_LIST:
            if word in normalized:
                return True, word
        
        # Check patterns
        for pattern in cls.OFFENSIVE_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return True, f"pattern:{pattern}"
        
        return False, None
    
    @classmethod
    def is_bot_username(cls, username: str) -> Tuple[bool, Optional[str]]:
        """
        Check if username looks like a bot/spam account.
        Returns (is_bot, matched_pattern)
        """
        if not username:
            return False, None
        
        username_lower = username.lower()
        
        for pattern in cls.BOT_PATTERNS:
            if re.search(pattern, username_lower, re.IGNORECASE):
                return True, pattern
        
        # Check for excessive numbers
        numbers = re.findall(r'\d', username)
        if len(numbers) > len(username) / 2:
            return True, "excessive_numbers"
        
        # Check for random-looking strings (high consonant ratio)
        consonants = re.findall(r'[bcdfghjklmnpqrstvwxyz]', username_lower)
        if len(username) > 5 and len(consonants) > len(username) * 0.8:
            return True, "random_looking"
        
        return False, None
    
    @classmethod
    def _normalize_leetspeak(cls, text: str) -> str:
        """
        Convert common leetspeak substitutions to normal letters.
        """
        substitutions = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
            '7': 't', '8': 'b', '@': 'a', '$': 's', '!': 'i',
            '+': 't', '(': 'c', ')': 'd',
        }
        
        result = text
        for leet, normal in substitutions.items():
            result = result.replace(leet, normal)
        
        return result


class BotDetector:
    """
    Advanced bot detection using fingerprint analysis and behavioral patterns.
    """
    
    # Known bot User-Agent patterns
    BOT_USER_AGENTS = [
        'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'python-requests',
        'headless', 'phantom', 'selenium', 'puppeteer', 'playwright',
        'httpclient', 'java/', 'perl/', 'ruby/', 'go-http-client',
    ]
    
    # Suspicious User-Agent characteristics
    SUSPICIOUS_UA_PATTERNS = [
        r'^Mozilla/[45]\.0 \(compatible',  # Very old/fake UA
        r'MSIE [5-8]\.',                   # Ancient IE
        r'Googlebot',                       # Search engine bots
        r'bingbot',
        r'Yandex',
        r'Baidu',
    ]
    
    @classmethod
    def analyze_fingerprint(cls, fingerprint: str, ip_address: str, 
                           user_agent: str, timezone: str = None) -> Tuple[bool, str, int]:
        """
        Analyze the provided fingerprint and metadata for bot indicators.
        
        Returns:
            (is_suspicious, reason, risk_score)
            risk_score: 0-100, higher = more suspicious
        """
        risk_score = 0
        reasons = []
        
        # 1. Check fingerprint validity
        if not fingerprint or len(fingerprint) < 20:
            risk_score += 40
            reasons.append("invalid_fingerprint")
        
        # 2. Check User-Agent
        ua_lower = user_agent.lower() if user_agent else ""
        
        for bot_ua in cls.BOT_USER_AGENTS:
            if bot_ua in ua_lower:
                risk_score += 50
                reasons.append(f"bot_ua:{bot_ua}")
                break
        
        for pattern in cls.SUSPICIOUS_UA_PATTERNS:
            if re.search(pattern, user_agent or "", re.IGNORECASE):
                risk_score += 20
                reasons.append(f"suspicious_ua_pattern")
                break
        
        # 3. Check for empty or suspicious User-Agent
        if not user_agent or len(user_agent) < 10:
            risk_score += 30
            reasons.append("empty_or_short_ua")
        
        # 4. Check for missing browser characteristics
        if user_agent:
            if 'Mozilla' not in user_agent and 'Chrome' not in user_agent:
                risk_score += 15
                reasons.append("non_browser_ua")
        
        # 5. Check timezone
        if timezone:
            try:
                # Very suspicious if timezone is undefined or unusual
                if timezone in ['undefined', 'null', '', 'UTC']:
                    risk_score += 10
                    reasons.append("suspicious_timezone")
            except:
                pass
        
        # 6. Rate limiting check via cache
        ip_key = f"reg_attempt:{ip_address}"
        fp_key = f"reg_attempt:{fingerprint}"
        
        ip_count = cache.get(ip_key, 0)
        fp_count = cache.get(fp_key, 0)
        
        if ip_count > 10:
            risk_score += 30
            reasons.append("high_ip_frequency")
        
        if fp_count > 5:
            risk_score += 40
            reasons.append("high_fingerprint_frequency")
        
        # Determine if suspicious
        is_suspicious = risk_score >= 50
        reason = ", ".join(reasons) if reasons else "clean"
        
        return is_suspicious, reason, risk_score
    
    @classmethod
    def record_attempt(cls, fingerprint: str, ip_address: str):
        """
        Record a registration attempt for rate limiting.
        """
        ip_key = f"reg_attempt:{ip_address}"
        fp_key = f"reg_attempt:{fingerprint}"
        
        # Increment counters (expire after 1 hour)
        ip_count = cache.get(ip_key, 0)
        fp_count = cache.get(fp_key, 0)
        
        cache.set(ip_key, ip_count + 1, 3600)
        cache.set(fp_key, fp_count + 1, 3600)


class VerificationCodeManager:
    """
    Manages verification codes for email and phone verification.
    Uses cache for temporary code storage.
    """
    
    CODE_LENGTH = 6
    CODE_EXPIRY = 600  # 10 minutes
    MAX_ATTEMPTS = 5
    
    @classmethod
    def generate_code(cls) -> str:
        """Generate a random 6-digit verification code."""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(cls.CODE_LENGTH)])
    
    @classmethod
    def store_email_code(cls, email: str, code: str):
        """Store verification code for email."""
        key = f"email_verify:{hashlib.md5(email.lower().encode()).hexdigest()}"
        cache.set(key, {
            'code': code,
            'attempts': 0,
            'created_at': time.time()
        }, cls.CODE_EXPIRY)
    
    @classmethod
    def store_phone_code(cls, phone: str, code: str):
        """Store verification code for phone."""
        # Normalize phone number
        normalized = re.sub(r'[^\d+]', '', phone)
        key = f"phone_verify:{hashlib.md5(normalized.encode()).hexdigest()}"
        cache.set(key, {
            'code': code,
            'attempts': 0,
            'created_at': time.time()
        }, cls.CODE_EXPIRY)
    
    @classmethod
    def verify_email_code(cls, email: str, code: str) -> Tuple[bool, str]:
        """
        Verify the email code.
        Returns (success, message)
        """
        key = f"email_verify:{hashlib.md5(email.lower().encode()).hexdigest()}"
        data = cache.get(key)
        
        if not data:
            return False, _("Verification code expired or not found. Please request a new code.")
        
        if data['attempts'] >= cls.MAX_ATTEMPTS:
            cache.delete(key)
            return False, _("Too many attempts. Please request a new code.")
        
        if data['code'] != code:
            data['attempts'] += 1
            cache.set(key, data, cls.CODE_EXPIRY)
            return False, _("Invalid verification code. Please try again.")
        
        # Success - delete the code
        cache.delete(key)
        return True, _("Email verified successfully!")
    
    @classmethod
    def verify_phone_code(cls, phone: str, code: str) -> Tuple[bool, str]:
        """
        Verify the phone code.
        Returns (success, message)
        """
        normalized = re.sub(r'[^\d+]', '', phone)
        key = f"phone_verify:{hashlib.md5(normalized.encode()).hexdigest()}"
        data = cache.get(key)
        
        if not data:
            return False, _("Verification code expired or not found. Please request a new code.")
        
        if data['attempts'] >= cls.MAX_ATTEMPTS:
            cache.delete(key)
            return False, _("Too many attempts. Please request a new code.")
        
        if data['code'] != code:
            data['attempts'] += 1
            cache.set(key, data, cls.CODE_EXPIRY)
            return False, _("Invalid verification code. Please try again.")
        
        # Success - delete the code
        cache.delete(key)
        return True, _("Phone verified successfully!")


class EmailService:
    """
    Email sending service for verification codes.
    Uses Django's email backend.
    """
    
    @classmethod
    def send_verification_code(cls, email: str, code: str, username: str = None) -> bool:
        """
        Send verification code to email.
        Returns True if sent successfully.
        """
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        
        try:
            subject = _("Rashigo - Email Verification Code")
            
            # Plain text version
            plain_message = _("""
Hello{username_greeting},

Your verification code for Rashigo is: {code}

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.

Best regards,
Rashigo Team
            """).format(
                username_greeting=f" {username}" if username else "",
                code=code
            )
            
            # HTML version
            html_message = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background: #1A1A1A; color: #E5E5E5; padding: 20px;">
                <div style="max-width: 500px; margin: 0 auto; background: #2A2A2A; padding: 30px; border-radius: 12px;">
                    <h2 style="color: #6366F1; margin-bottom: 20px;">🔐 Email Verification</h2>
                    <p>Hello{' ' + username if username else ''},</p>
                    <p>Your verification code for Rashigo is:</p>
                    <div style="background: #6366F1; color: white; font-size: 32px; font-weight: bold; text-align: center; padding: 20px; border-radius: 8px; letter-spacing: 8px; margin: 20px 0;">
                        {code}
                    </div>
                    <p style="color: #9CA3AF; font-size: 14px;">This code will expire in 10 minutes.</p>
                    <hr style="border: none; border-top: 1px solid #3A3A3A; margin: 20px 0;">
                    <p style="color: #6B7280; font-size: 12px;">If you did not request this code, please ignore this email.</p>
                </div>
            </body>
            </html>
            """
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@rashigo.com',
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False
            )
            return True
            
        except Exception as e:
            print(f"Email send error: {e}")
            return False


class SMSService:
    """
    SMS sending service for phone verification.
    This is a placeholder - implement with your preferred SMS provider.
    
    Supported providers (implement as needed):
    - Twilio
    - Nexmo (Vonage)
    - AWS SNS
    - Messagebird
    """
    
    @classmethod
    def send_verification_code(cls, phone: str, code: str) -> bool:
        """
        Send verification code via SMS.
        
        PLACEHOLDER: Implement with your SMS provider.
        Returns True if sent successfully.
        """
        # Normalize phone number
        normalized = re.sub(r'[^\d+]', '', phone)
        
        # Validate phone format
        if not normalized or len(normalized) < 10:
            return False
        
        # ============================================
        # TWILIO IMPLEMENTATION (uncomment to use)
        # ============================================
        # from twilio.rest import Client
        # 
        # account_sid = settings.TWILIO_ACCOUNT_SID
        # auth_token = settings.TWILIO_AUTH_TOKEN
        # from_number = settings.TWILIO_FROM_NUMBER
        # 
        # client = Client(account_sid, auth_token)
        # 
        # try:
        #     message = client.messages.create(
        #         body=f"Your Rashigo verification code is: {code}",
        #         from_=from_number,
        #         to=normalized
        #     )
        #     return True
        # except Exception as e:
        #     print(f"SMS send error: {e}")
        #     return False
        # ============================================
        
        # For development/testing - just log the code
        print(f"[SMS PLACEHOLDER] Sending code {code} to {normalized}")
        
        # In development, always return True
        # In production, implement real SMS sending
        return True

