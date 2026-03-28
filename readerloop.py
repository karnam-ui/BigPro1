import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os

# Create VNR folder if it doesn't exist
if not os.path.exists("VNR"):
    os.makedirs("VNR")

# Read links from home.txt
with open("VNR/home.txt", "r", encoding="utf-8") as f:
    content = f.read()

# Extract the Links section
links_section = content.split("Links:\n")
if len(links_section) > 1:
    links_text = links_section[1]
    links = [line.strip() for line in links_text.split("\n") if line.strip()]
else:
    print("No links section found in home.txt")
    links = []

# Filter valid URLs (exclude relative links, anchors, and tel links)
valid_links = []
for link in links:
    if link.startswith("http://") or link.startswith("https://"):
        valid_links.append(link)

print(f"Found {len(valid_links)} valid links to process\n")

# Process each link
for i, url in enumerate(valid_links, 1):
    try:
        print(f"Processing {i}/{len(valid_links)}: {url}")
        
        # Fetch the page
        web = requests.get(url, timeout=10)
        web.raise_for_status()
        
        # Parse the content
        soup = BeautifulSoup(web.content, "html.parser")
        
        # Extract headers, paragraphs, and links
        headers = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
        links_found = [a['href'] for a in soup.find_all('a', href=True)]
        
        # Generate filename from URL
        parsed_url = urlparse(url)
        path = parsed_url.path.strip("/").replace("/", "_")
        if not path:
            path = "index"
        filename = f"VNR/{path}.txt"
        
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
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error processing {url}: {e}\n")
    except Exception as e:
        print(f"✗ Unexpected error processing {url}: {e}\n")

print("Scraping completed!")
