import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import os
import re
import glob
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("Installing pdfplumber...")
    os.system("pip install pdfplumber")
    import pdfplumber

# Create VNR folder if it doesn't exist
if not os.path.exists("VNR"):
    os.makedirs("VNR")

# ===========================
# STEP 1: Remove duplicates across all txt files
# ===========================
print("=" * 80)
print("STEP 1: Removing duplicate content across all txt files...")
print("=" * 80)

def extract_content_only(text):
    """Extract only headers, paragraphs content (remove URL line and section headers)"""
    lines = text.split("\n")
    content_lines = []
    in_content = False
    
    for line in lines:
        # Skip URL line and section separator lines
        if line.startswith("URL:") or line.startswith("=" * 20) or line.startswith("HEADERS:") or line.startswith("PARAGRAPHS:") or line.startswith("LINKS:"):
            continue
        if line.strip():
            content_lines.append(line.strip())
    
    return set(content_lines)  # Return as set for deduplication

# Get all txt files
txt_files = glob.glob("VNR/*.txt")
all_seen_content = set()
files_modified = 0

for txt_file in txt_files:
    try:
        with open(txt_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        content_lines = extract_content_only(content)
        new_content = content_lines - all_seen_content
        
        if len(new_content) < len(content_lines):
            # File has duplicates, rewrite it
            with open(txt_file, "w", encoding="utf-8") as f:
                for line in sorted(new_content):
                    f.write(line + "\n")
            files_modified += 1
            print(f"✓ Cleaned {txt_file} (removed {len(content_lines) - len(new_content)} duplicates)")
        
        all_seen_content.update(new_content)
    except Exception as e:
        print(f"✗ Error processing {txt_file}: {e}")

print(f"\n✓ Modified {files_modified} files\n")

# ===========================
# STEP 2: Extract all unique links from all txt files
# ===========================
print("=" * 80)
print("STEP 2: Extracting all unique links from txt files...")
print("=" * 80)

all_links = set()
crawled_urls = set()

# Read home.txt for initial links
with open("VNR/home.txt", "r", encoding="utf-8") as f:
    home_content = f.read()
    links_section = home_content.split("Links:\n")
    if len(links_section) > 1:
        links_text = links_section[1]
        initial_links = [line.strip() for line in links_text.split("\n") if line.strip()]
        for link in initial_links:
            if link.startswith("http://") or link.startswith("https://"):
                all_links.add(link)

# Extract links from all txt files
for txt_file in txt_files:
    try:
        with open(txt_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find all URLs in content using regex
        url_pattern = r'https?://[^\s\]"\)]*'
        found_urls = re.findall(url_pattern, content)
        
        for url in found_urls:
            clean_url = url.rstrip('.,;:')
            if clean_url.startswith("http"):
                all_links.add(clean_url)
        
        # Track which URLs have been crawled
        if content.startswith("URL:"):
            url_line = content.split("\n")[0].replace("URL: ", "").strip()
            if url_line:
                crawled_urls.add(url_line)
    except Exception as e:
        print(f"✗ Error reading {txt_file}: {e}")

# ===========================
# STEP 3: Identify uncrawled links
# ===========================
print(f"Found {len(all_links)} unique links total")
print(f"Already crawled {len(crawled_urls)} URLs\n")

uncrawled_links = all_links - crawled_urls

# Filter out image and relative links
valid_uncrawled = []
for link in uncrawled_links:
    # Skip image files, except PDFs
    if link.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
        continue
    # Skip video files
    if link.endswith(('.mp4', '.mov', '.avi')):
        continue
    # Skip sheets
    if link.endswith('.xlsx'):
        continue
    # Skip tel and mailto
    if link.startswith('tel:') or link.startswith('mailto:'):
        continue
    # Skip anchor links
    if link.startswith('#'):
        continue
    # Skip localhost
    if 'localhost' in link or '127.0.0.1' in link:
        continue
    valid_uncrawled.append(link)

print(f"Found {len(valid_uncrawled)} new links to crawl\n")

if len(valid_uncrawled) == 0:
    print("No new links to crawl!")
else:
    # ===========================
    # STEP 4: Scrape new links
    # ===========================
    print("=" * 80)
    print("STEP 4: Scraping new links...")
    print("=" * 80 + "\n")
    
    for i, url in enumerate(valid_uncrawled, 1):
        try:
            print(f"Processing {i}/{len(valid_uncrawled)}: {url}")
            
            # Check if it's a PDF
            if url.endswith('.pdf'):
                # Handle PDF links
                print(f"  → Downloading PDF...")
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                
                # Extract text from PDF
                with open("temp.pdf", "wb") as pdf_file:
                    pdf_file.write(response.content)
                
                pdf_text = ""
                try:
                    with pdfplumber.open("temp.pdf") as pdf:
                        for page in pdf.pages:
                            pdf_text += page.extract_text() + "\n"
                except Exception as pdf_e:
                    print(f"  ! Warning: Could not extract text from PDF: {pdf_e}")
                
                # Generate filename
                parsed_url = urlparse(url)
                filename = parsed_url.path.split('/')[-1].replace('.pdf', '.txt')
                if not filename:
                    filename = "pdf_document.txt"
                filepath = f"VNR/{filename}"
                
                # Write PDF content to file
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"SOURCE PDF: {url}\n\n")
                    f.write("=" * 80 + "\n")
                    f.write("PDF CONTENT:\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(pdf_text)
                
                print(f"✓ Saved PDF content to {filepath}\n")
                
                # Cleanup temp file
                if os.path.exists("temp.pdf"):
                    os.remove("temp.pdf")
            else:
                # Handle regular HTML pages
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Extract headers, paragraphs, and links
                headers = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
                paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
                links_found = [a['href'] for a in soup.find_all('a', href=True)]
                
                # Generate filename from URL
                parsed_url = urlparse(url)
                path = parsed_url.path.strip("/").replace("/", "_").replace(".", "_")
                if not path:
                    path = "index"
                # Remove special characters
                path = re.sub(r'[^\w\-_]', '', path)
                filename = f"VNR/{path}.txt"
                
                # Avoid overwriting existing files
                counter = 1
                base_filename = filename[:-4]
                while os.path.exists(filename):
                    filename = f"{base_filename}_{counter}.txt"
                    counter += 1
                
                # Write to file
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"URL: {url}\n\n")
                    f.write("=" * 80 + "\n")
                    f.write("HEADERS:\n")
                    f.write("=" * 80 + "\n")
                    f.write("\n".join(headers) + "\n\n")
                    
                    f.write("=" * 80 + "\n")
                    f.write("PARAGRAPHS:\n")
                    f.write("=" * 80 + "\n")
                    f.write("\n".join(paragraphs) + "\n\n")
                    
                    f.write("=" * 80 + "\n")
                    f.write("LINKS:\n")
                    f.write("=" * 80 + "\n")
                    f.write("\n".join(links_found))
                
                print(f"✓ Saved to {filename}\n")
        
        except requests.exceptions.Timeout:
            print(f"✗ Timeout processing {url}\n")
        except requests.exceptions.RequestException as e:
            print(f"✗ Error processing {url}: {e}\n")
        except Exception as e:
            print(f"✗ Unexpected error processing {url}: {e}\n")

print("\n" + "=" * 80)
print("✓ All operations completed!")
print("=" * 80)
