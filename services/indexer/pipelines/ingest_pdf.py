"""
PDF ingestion pipeline for SearchIt
"""

import logging
from typing import List, Dict, Any, Optional
import io
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import yaml

logger = logging.getLogger(__name__)

class PDFIngester:
    """PDF document ingestion with OCR support"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        default_config = {
            "enable_ocr": True,
            "ocr_language": "eng",
            "extract_images": False,
            "max_pages": 1000,
            "text_extraction_method": "auto",  # auto, pymupdf, ocr
            "image_dpi": 300,
            "ocr_confidence_threshold": 60
        }
        
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    default_config.update(config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def ingest_pdf(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """Ingest a PDF file and extract text content"""
        try:
            logger.info(f"Processing PDF: {pdf_path}")
            
            # Open PDF document
            doc = fitz.open(pdf_path)
            
            if len(doc) > self.config["max_pages"]:
                logger.warning(f"PDF has {len(doc)} pages, limiting to {self.config['max_pages']}")
            
            # Extract metadata
            metadata = doc.metadata
            title = metadata.get("title", "") or pdf_path.split("/")[-1]
            
            # Extract text from all pages
            full_text = ""
            pages_content = []
            
            for page_num in range(min(len(doc), self.config["max_pages"])):
                page = doc[page_num]
                page_content = self._extract_page_content(page, page_num)
                
                if page_content["text"]:
                    full_text += page_content["text"] + "\n\n"
                    pages_content.append(page_content)
            
            doc.close()
            
            # Clean and normalize text
            full_text = self._clean_text(full_text)
            
            if not full_text.strip():
                logger.warning(f"No text extracted from PDF: {pdf_path}")
                return None
            
            return {
                "title": title,
                "text": full_text,
                "pages": pages_content,
                "metadata": metadata,
                "source": "pdf",
                "file_path": pdf_path,
                "page_count": len(pages_content)
            }
            
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")
            return None
    
    def _extract_page_content(self, page, page_num: int) -> Dict[str, Any]:
        """Extract content from a single PDF page"""
        page_content = {
            "page_number": page_num + 1,
            "text": "",
            "images": [],
            "extraction_method": "none"
        }
        
        try:
            # Try PyMuPDF text extraction first
            text = page.get_text()
            
            if text.strip() and len(text.strip()) > 50:
                # Good text extraction from PyMuPDF
                page_content["text"] = text.strip()
                page_content["extraction_method"] = "pymupdf"
            elif self.config["enable_ocr"]:
                # Fall back to OCR
                ocr_text = self._extract_text_with_ocr(page)
                if ocr_text:
                    page_content["text"] = ocr_text
                    page_content["extraction_method"] = "ocr"
            
            # Extract images if enabled
            if self.config["extract_images"]:
                images = self._extract_images_from_page(page, page_num)
                page_content["images"] = images
            
        except Exception as e:
            logger.error(f"Failed to extract content from page {page_num}: {e}")
        
        return page_content
    
    def _extract_text_with_ocr(self, page) -> Optional[str]:
        """Extract text using OCR"""
        try:
            # Convert page to image
            mat = fitz.Matrix(self.config["image_dpi"] / 72, self.config["image_dpi"] / 72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(img_data))
            
            # Perform OCR
            ocr_config = f'--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?;:()[]{{}}"- '
            text = pytesseract.image_to_string(
                image, 
                lang=self.config["ocr_language"],
                config=ocr_config
            )
            
            # Clean OCR text
            text = self._clean_ocr_text(text)
            
            if len(text.strip()) > 20:  # Minimum text length threshold
                return text.strip()
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
        
        return None
    
    def _extract_images_from_page(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Extract images from a PDF page"""
        images = []
        
        try:
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    # Get image data
                    xref = img[0]
                    pix = fitz.Pixmap(page.parent, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")
                        
                        images.append({
                            "index": img_index,
                            "page_number": page_num + 1,
                            "data": img_data,
                            "format": "png",
                            "width": pix.width,
                            "height": pix.height
                        })
                    
                    pix = None
                    
                except Exception as e:
                    logger.error(f"Failed to extract image {img_index} from page {page_num}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to extract images from page {page_num}: {e}")
        
        return images
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        import re
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers (simple heuristics)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip very short lines that are likely page numbers
            if len(line) <= 3 and line.isdigit():
                continue
            
            # Skip lines that are all punctuation
            if re.match(r'^[^\w\s]*$', line):
                continue
            
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()
    
    def _clean_ocr_text(self, text: str) -> str:
        """Clean OCR-extracted text"""
        import re
        
        # Remove OCR artifacts
        text = re.sub(r'[|]', 'I', text)  # Common OCR mistake
        text = re.sub(r'[0O]', 'O', text)  # Another common mistake
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove lines that are mostly punctuation
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip lines that are mostly non-alphanumeric
            if line and len(re.sub(r'[^\w]', '', line)) < len(line) * 0.5:
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

def ingest_pdf_file(pdf_path: str) -> Optional[Dict[str, Any]]:
    """Convenience function to ingest a single PDF file"""
    ingester = PDFIngester()
    return ingester.ingest_pdf(pdf_path)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ingest_pdf.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    result = ingest_pdf_file(pdf_path)
    
    if result:
        print(f"Title: {result['title']}")
        print(f"Pages: {result['page_count']}")
        print(f"Text length: {len(result['text'])}")
        print(f"Text preview: {result['text'][:200]}...")
    else:
        print("Failed to process PDF")
