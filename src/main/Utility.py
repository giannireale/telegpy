import re
from urllib.parse import urlparse


def extract_asin(url):
    # Parse the URL
    parsed_url = urlparse(url)

    # Regex pattern per trovare l'ASIN
    # Cerca uno di questi formati: '/dp/ASIN', '/gp/product/ASIN', '/product/ASIN'
    asin_pattern = r'/dp/([A-Z0-9]{10})|/gp/product/([A-Z0-9]{10})|/product/([A-Z0-9]{10})|/([A-Z0-9]{10})(?=[/?])'

    # Cerca il pattern nel percorso dell'URL
    match = re.search(asin_pattern, parsed_url.path)

    if match:
        # match.group(n) restituirà il gruppo corrispondente, quindi dobbiamo verificare quale gruppo è non-None
        for group in match.groups():
            if group:
                return group
    return None
