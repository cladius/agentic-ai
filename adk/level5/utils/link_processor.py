import logging
import requests
from typing import Optional
from bs4 import BeautifulSoup
from level5.utils.chroma_db_manager import ChromaDBManager

logger = logging.getLogger(__name__)


"""This module provides utilities for processing links, extracting content, and storing it in a ChromaDB database."""
class LinkProcessor:
    def __init__(self, chroma_manager: ChromaDBManager):
        self.chroma_manager = chroma_manager

    def process_link(self, url: str) -> Optional[str]:
        """
        Process a URL and extract relevant content.
        
        Args:
            url: The URL to process.
            
        Returns:
            Optional[str]: Document ID if processing succeeds, None if it fails.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get('content-type', '').lower()
            
            if 'text/html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator='\n', strip=True)
                return self.chroma_manager.store_document(url, text, "text")
            
            elif 'image/' in content_type:
                return self.chroma_manager.store_document(url, url, "image")
            
            elif 'application/pdf' in content_type:
                return self.chroma_manager.store_document(url, url, "pdf")
            
            else:
                return self.chroma_manager.store_document(url, response.text, "other")
                
        except Exception as e:
            logger.error(f"Error processing link {url}: {str(e)}")
            return None