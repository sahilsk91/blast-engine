import asyncio
import aiohttp
import re
from io import BytesIO
import pytesseract
from PIL import Image

# Email extraction regex for OCR (sometimes spaces or [] get added around @ and .)
OCR_EMAIL_PATTERN = r'[a-zA-Z0-9_.+-]+(?:\s*@\s*|\s*\[at\]\s*)[a-zA-Z0-9-]+(?:\s*\.\s*|\s*\[dot\]\s*)[a-zA-Z0-9-.]+'

def clean_ocr_email(raw_email: str) -> str:
    """Cleans up obfuscated or poorly read emails."""
    e = raw_email.lower().replace(" ", "")
    e = e.replace("[at]", "@").replace("(at)", "@")
    e = e.replace("[dot]", ".").replace("(dot)", ".")
    return e

async def download_image(session: aiohttp.ClientSession, url: str) -> bytes:
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                return await resp.read()
    except Exception:
        pass
    return b""

async def extract_emails_from_images(md_content: str, session: aiohttp.ClientSession) -> list[str]:
    """
    V6 God-Tier: AI Vision Fallback.
    Scans the Firecrawl markdown for image tags (![alt](url)).
    Downloads the images and runs Tesseract OCR to find obfuscated emails.
    """
    # 1. Extract image URLs from markdown
    image_urls = re.findall(r'!\[.*?\]\((.*?)\)', md_content)
    
    # 2. Filter images - prioritize contact, email headers, or standard formats.
    #    To save CPU, we limit to 5 images max.
    priority_urls = []
    for url in image_urls:
        if any(keyword in url.lower() for keyword in ["contact", "email", "header", "footer", "support"]):
            priority_urls.insert(0, url)
        else:
            priority_urls.append(url)
            
    priority_urls = priority_urls[:5] # Process max 5 images to avoid massive CPU load
    
    if not priority_urls:
        return []
        
    emails_found = []
    
    # 3. Download and OCR in parallel
    tasks = [download_image(session, u) for u in priority_urls]
    image_bytes_list = await asyncio.gather(*tasks)
    
    for img_bytes in image_bytes_list:
        if not img_bytes:
            continue
            
        try:
            # 4. Run Tesseract Vision
            image = Image.open(BytesIO(img_bytes))
            text = pytesseract.image_to_string(image)
            
            # 5. Extract and de-obfuscate emails
            matches = re.findall(OCR_EMAIL_PATTERN, text)
            for m in matches:
                clean = clean_ocr_email(m)
                # Keep basic noise filter here
                if not any(junk in clean for junk in ["example.com", "yourdomain"]):
                    emails_found.append(clean)
        except Exception as e:
            # Catch PIL errors or Tesseract missing errors without crashing
            continue
            
    return list(set(emails_found))

# Manual Test
if __name__ == "__main__":
    test_md = "Here is my image: ![contact](https://dummyimage.com/600x400/fff/000.png&text=john%40gmail.com)"
    # Would need an active event loop to test, this module will be called by firecrawl_client.py
    print("[V6 Vision] Module Loaded.")
