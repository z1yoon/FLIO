"""
Azure Translation Service for Korean to English text translation.
Optimizes embedding costs by translating Korean text to English before processing.
"""

import os
import logging
from typing import Optional, List
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError

logger = logging.getLogger(__name__)


class TranslationService:
    """Service for translating Korean text to English using Azure Translator."""
    
    def __init__(self):
        """Initialize Azure Translator client."""
        self.endpoint = os.getenv("AZURE_TRANSLATOR_ENDPOINT")
        self.key = os.getenv("AZURE_TRANSLATOR_KEY")
        self.region = os.getenv("AZURE_TRANSLATOR_REGION", "koreacentral")
        
        if not self.endpoint or not self.key:
            logger.warning("Azure Translator credentials not configured. Translation will be skipped.")
            self.client = None
        else:
            try:
                self.client = TextTranslationClient(
                    endpoint=self.endpoint,
                    credential=AzureKeyCredential(self.key),
                    region=self.region
                )
                logger.info("Azure Translator client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Azure Translator: {e}")
                self.client = None
    
    async def translate_to_english(self, korean_text: str) -> str:
        """
        Translate Korean text to English.
        
        Args:
            korean_text: Korean text to translate
            
        Returns:
            Translated English text, or original text if translation fails
        """
        if not self.client:
            logger.warning("Translator not available, returning original text")
            return korean_text
        
        if not korean_text or not korean_text.strip():
            return korean_text
        
        try:
            # Translate Korean to English
            response = self.client.translate(
                body=[{"text": korean_text}],
                from_language="ko",
                to_language="en"
            )
            
            if response and len(response) > 0:
                translations = response[0].translations
                if translations and len(translations) > 0:
                    translated_text = translations[0].text
                    logger.info(f"Translated text: {len(korean_text)} chars (KO) -> {len(translated_text)} chars (EN)")
                    return translated_text
            
            logger.warning("No translation result, returning original text")
            return korean_text
            
        except AzureError as e:
            logger.error(f"Azure translation error: {e}")
            return korean_text
        except Exception as e:
            logger.error(f"Unexpected translation error: {e}")
            return korean_text
    
    async def translate_batch_to_english(self, korean_texts: List[str]) -> List[str]:
        """
        Translate multiple Korean texts to English in a single batch.
        More efficient for multiple texts.
        
        Args:
            korean_texts: List of Korean texts to translate
            
        Returns:
            List of translated English texts
        """
        if not self.client:
            logger.warning("Translator not available, returning original texts")
            return korean_texts
        
        if not korean_texts:
            return []
        
        try:
            # Prepare batch request
            body = [{"text": text} for text in korean_texts if text and text.strip()]
            
            if not body:
                return korean_texts
            
            # Translate batch
            response = self.client.translate(
                body=body,
                from_language="ko",
                to_language="en"
            )
            
            if not response:
                logger.warning("No batch translation result, returning original texts")
                return korean_texts
            
            # Extract translated texts
            translated_texts = []
            for item in response:
                if item.translations and len(item.translations) > 0:
                    translated_texts.append(item.translations[0].text)
                else:
                    # Fallback to original if translation failed
                    idx = len(translated_texts)
                    translated_texts.append(korean_texts[idx] if idx < len(korean_texts) else "")
            
            logger.info(f"Batch translated {len(translated_texts)} texts")
            return translated_texts
            
        except AzureError as e:
            logger.error(f"Azure batch translation error: {e}")
            return korean_texts
        except Exception as e:
            logger.error(f"Unexpected batch translation error: {e}")
            return korean_texts
    
    async def translate_to_korean(self, english_text: str) -> str:
        """
        Translate English text back to Korean.
        Used for translating AI-generated responses back to Korean.
        
        Args:
            english_text: English text to translate
            
        Returns:
            Translated Korean text, or original text if translation fails
        """
        if not self.client:
            logger.warning("Translator not available, returning original text")
            return english_text
        
        if not english_text or not english_text.strip():
            return english_text
        
        try:
            # Translate English to Korean
            response = self.client.translate(
                body=[{"text": english_text}],
                from_language="en",
                to_language="ko"
            )
            
            if response and len(response) > 0:
                translations = response[0].translations
                if translations and len(translations) > 0:
                    translated_text = translations[0].text
                    logger.info(f"Translated text: {len(english_text)} chars (EN) -> {len(translated_text)} chars (KO)")
                    return translated_text
            
            logger.warning("No translation result, returning original text")
            return english_text
            
        except AzureError as e:
            logger.error(f"Azure translation error: {e}")
            return english_text
        except Exception as e:
            logger.error(f"Unexpected translation error: {e}")
            return english_text


# Singleton instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get or create the translation service singleton."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service
