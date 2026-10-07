"""
Language detection utilities - English only
"""

from typing import Any, Dict


def detect_language(text: str) -> str:
    """
    Returns 'en' for English
    """
    return "en"


def get_language_config(language: str) -> Dict[str, Any]:
    """
    Get configuration for specific language (always English)
    """
    return {
        "name": "English",
        "code": "en",
        "greeting": "Hello",
        "thank_you": "Thank you",
        "welcome": "Welcome",
        "help": "help",
        "delivery": "delivery",
        "otp": "OTP",
    }


def format_mixed_text(text: str, target_language: str) -> str:
    """
    Format text for better pronunciation
    """
    return text


def get_response_templates(language: str) -> Dict[str, str]:
    """
    Get response templates for English
    """
    return {
        "greeting": "Hello! How may I assist you today?",
        "delivery_help": "Thank you! I can help with your delivery. Are you here or do you need directions?",
        "need_directions": "I'll help you get here. Let me get the directions for you.",
        "arrived": "Great! You've arrived. Do you need the OTP for delivery?",
        "otp_provide": "Here's your OTP for {company}: {otp}",
        "unknown_caller": "Hello! I'm an AI assistant. May I know who's calling and how I can help you?",
        "collect_name": "May I know who's calling?",
        "collect_purpose": "Thanks {name}. What's the purpose of your call today?",
        "urgent_matter": "This seems urgent. I'll notify the owner immediately.",
        "callback_info": "I'll let them know you called. Is {phone} the best number to reach you?",
    }
