"""
Text cleaning and normalization pipeline
"""

import logging
import re
from typing import List, Dict, Any, Optional
from langdetect import detect, LangDetectException
import yaml

logger = logging.getLogger(__name__)

class TextCleaner:
    """Text cleaning and normalization utilities"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        default_config = {
            "remove_extra_whitespace": True,
            "normalize_unicode": True,
            "remove_control_chars": True,
            "remove_html_tags": True,
            "normalize_quotes": True,
            "remove_extra_punctuation": False,
            "language_detection": {
                "enabled": True,
                "fallback_lang": "en",
                "min_confidence": 0.7
            },
            "boilerplate_removal": {
                "enabled": True,
                "patterns": [
                    r"^\s*\d+\s*$",  # Page numbers
                    r"^[^\w\s]*$",   # Lines with only punctuation
                    r"^\s*[|_\-=]+\s*$",  # Separator lines
                    r"^\s*Copyright.*$",  # Copyright notices
                    r"^\s*All rights reserved.*$"
                ]
            }
        }
        
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    default_config.update(config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        logger.debug(f"Cleaning text of length {len(text)}")
        
        # Remove HTML tags if enabled
        if self.config["remove_html_tags"]:
            text = self._remove_html_tags(text)
        
        # Remove control characters
        if self.config["remove_control_chars"]:
            text = self._remove_control_chars(text)
        
        # Normalize unicode
        if self.config["normalize_unicode"]:
            text = self._normalize_unicode(text)
        
        # Normalize quotes
        if self.config["normalize_quotes"]:
            text = self._normalize_quotes(text)
        
        # Remove extra whitespace
        if self.config["remove_extra_whitespace"]:
            text = self._remove_extra_whitespace(text)
        
        # Remove boilerplate content
        if self.config["boilerplate_removal"]["enabled"]:
            text = self._remove_boilerplate(text)
        
        # Remove extra punctuation if enabled
        if self.config["remove_extra_punctuation"]:
            text = self._remove_extra_punctuation(text)
        
        return text.strip()
    
    def _remove_html_tags(self, text: str) -> str:
        """Remove HTML tags from text"""
        # Remove script and style content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' '
        }
        
        for entity, char in html_entities.items():
            text = text.replace(entity, char)
        
        return text
    
    def _remove_control_chars(self, text: str) -> str:
        """Remove control characters"""
        # Remove null bytes and other control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Remove zero-width characters
        text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)
        
        return text
    
    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters"""
        import unicodedata
        
        # Normalize unicode to NFC form
        text = unicodedata.normalize('NFC', text)
        
        # Replace common unicode variants with ASCII equivalents
        unicode_replacements = {
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '–': '-',
            '—': '-',
            '…': '...',
            '•': '*',
            '°': ' degrees',
            '×': 'x',
            '÷': '/',
            '±': '+/-'
        }
        
        for unicode_char, ascii_char in unicode_replacements.items():
            text = text.replace(unicode_char, ascii_char)
        
        return text
    
    def _normalize_quotes(self, text: str) -> str:
        """Normalize various quote characters"""
        quote_replacements = {
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '`': "'",
            '´': "'"
        }
        
        for quote_char, replacement in quote_replacements.items():
            text = text.replace(quote_char, replacement)
        
        return text
    
    def _remove_extra_whitespace(self, text: str) -> str:
        """Remove excessive whitespace"""
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove trailing whitespace from lines
        lines = text.split('\n')
        lines = [line.rstrip() for line in lines]
        
        return '\n'.join(lines)
    
    def _remove_boilerplate(self, text: str) -> str:
        """Remove boilerplate content using regex patterns"""
        lines = text.split('\n')
        cleaned_lines = []
        
        patterns = self.config["boilerplate_removal"]["patterns"]
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                cleaned_lines.append('')
                continue
            
            # Check against boilerplate patterns
            is_boilerplate = False
            for pattern in patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    is_boilerplate = True
                    break
            
            if not is_boilerplate:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _remove_extra_punctuation(self, text: str) -> str:
        """Remove excessive punctuation"""
        # Remove multiple consecutive punctuation marks
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        text = re.sub(r'[.]{3,}', '...', text)
        
        return text
    
    def detect_language(self, text: str) -> str:
        """Detect the language of text"""
        if not self.config["language_detection"]["enabled"]:
            return self.config["language_detection"]["fallback_lang"]
        
        try:
            # Use a sample of the text for detection (first 1000 chars)
            sample_text = text[:1000]
            if len(sample_text.strip()) < 50:
                return self.config["language_detection"]["fallback_lang"]
            
            detected_lang = detect(sample_text)
            
            # Map common language codes
            lang_mapping = {
                'en': 'en',
                'es': 'es', 
                'fr': 'fr',
                'de': 'de',
                'it': 'it',
                'pt': 'pt',
                'ru': 'ru',
                'zh-cn': 'zh',
                'zh': 'zh',
                'ja': 'ja',
                'ko': 'ko'
            }
            
            return lang_mapping.get(detected_lang, self.config["language_detection"]["fallback_lang"])
            
        except LangDetectException:
            logger.warning("Language detection failed, using fallback")
            return self.config["language_detection"]["fallback_lang"]
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return self.config["language_detection"]["fallback_lang"]
    
    def extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """Extract sections from text based on headings"""
        sections = []
        
        # Split by common heading patterns
        heading_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headings
            r'^\d+\.\s+(.+)$',   # Numbered sections
            r'^[A-Z][A-Z\s]+$'   # ALL CAPS headings
        ]
        
        lines = text.split('\n')
        current_section = {
            "title": "",
            "content": "",
            "level": 0
        }
        
        for line in lines:
            line = line.strip()
            
            # Check if line is a heading
            is_heading = False
            for pattern in heading_patterns:
                match = re.match(pattern, line)
                if match:
                    # Save previous section if it has content
                    if current_section["content"].strip():
                        sections.append(current_section.copy())
                    
                    # Start new section
                    current_section = {
                        "title": match.group(1) if match.groups() else line,
                        "content": "",
                        "level": len(match.group(1)) if pattern.startswith('^#') else 1
                    }
                    is_heading = True
                    break
            
            if not is_heading and line:
                current_section["content"] += line + "\n"
        
        # Add final section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections

def clean_and_normalize_text(text: str, config_path: str = None) -> Dict[str, Any]:
    """Convenience function to clean and normalize text"""
    cleaner = TextCleaner(config_path)
    
    cleaned_text = cleaner.clean_text(text)
    language = cleaner.detect_language(cleaned_text)
    sections = cleaner.extract_sections(cleaned_text)
    
    return {
        "original_text": text,
        "cleaned_text": cleaned_text,
        "language": language,
        "sections": sections,
        "word_count": len(cleaned_text.split()),
        "char_count": len(cleaned_text)
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python clean_normalize.py <text_file>")
        sys.exit(1)
    
    text_file = sys.argv[1]
    
    with open(text_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    result = clean_and_normalize_text(text)
    
    print(f"Language: {result['language']}")
    print(f"Word count: {result['word_count']}")
    print(f"Character count: {result['char_count']}")
    print(f"Sections: {len(result['sections'])}")
    print(f"Cleaned text preview: {result['cleaned_text'][:200]}...")
