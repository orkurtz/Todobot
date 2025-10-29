"""
Media handling utilities for WhatsApp files
"""
import os
import requests
from typing import Optional, Tuple

class MediaHandler:
    """Handle WhatsApp media downloads"""
    
    def __init__(self):
        self.whatsapp_token = os.getenv('WHATSAPP_TOKEN')
        self.whatsapp_api_base = "https://graph.facebook.com/v22.0"
    
    def download_whatsapp_media(self, media_id: str) -> Optional[Tuple[bytes, str]]:
        """
        Download media file from WhatsApp
        
        Returns:
            Tuple of (file_bytes, mime_type) or None if failed
        """
        try:
            # Step 1: Get media URL and metadata
            url = f"{self.whatsapp_api_base}/{media_id}"
            headers = {
                'Authorization': f'Bearer {self.whatsapp_token}'
            }
            
            print(f"🔽 Fetching media metadata for ID: {media_id}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Failed to get media URL: {response.status_code} - {response.text}")
                return None
            
            media_data = response.json()
            media_url = media_data.get('url')
            mime_type = media_data.get('mime_type', 'audio/ogg')
            
            if not media_url:
                print("❌ No media URL in response")
                return None
            
            # Step 2: Download the actual media file
            print(f"🔽 Downloading media from URL...")
            download_response = requests.get(media_url, headers=headers, timeout=30)
            
            if download_response.status_code != 200:
                print(f"❌ Failed to download media: {download_response.status_code}")
                return None
            
            file_bytes = download_response.content
            print(f"✅ Downloaded media file: {len(file_bytes)} bytes, type: {mime_type}")
            
            return (file_bytes, mime_type)
            
        except requests.exceptions.Timeout:
            print("❌ Timeout downloading media from WhatsApp")
            return None
        except Exception as e:
            print(f"❌ Error downloading WhatsApp media: {e}")
            return None

# Create singleton instance
media_handler = MediaHandler()

