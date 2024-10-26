import os
import uuid
import logging
from dotenv import load_dotenv
from openai import OpenAI
import requests

# Load environment variables from .env file
load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pexels_api_key = os.getenv("PEXELS_API_KEY")
pixabay_api_key = os.getenv("PIXABAY_API_KEY") or ''

def download_image(image_url):
    response = requests.get(image_url)
    #save the image to the assets folder
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'images')
    os.makedirs(assets_dir, exist_ok=True)
    image_path = os.path.join(assets_dir, f"{uuid.uuid4()}.jpg")
    with open(image_path, 'wb') as f:
        f.write(response.content)
    return image_path

def search_pexels_images(query):
    """Search for images using Pexels API and return the URLs."""
    search_url = "https://api.pexels.com/v1/search"

    headers = {
        'Authorization': pexels_api_key
    }
    
    params = {
        'query': query,
        'per_page': 2
    }
    
    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()  # Raise an error for bad responses
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error occurred: {e}")  # Log the error
        return []  # Return an empty list on error
    except Exception as e:
        logging.error(f"An error occurred during the request: {e}")
        return []

    search_results = response.json()
    image_urls = [photo['src']['original'] for photo in search_results.get('photos', [])]  # Extract image URLs
    return image_urls[0]

def search_pixabay_images(query):
    """Search for images using Pixabay API and return the URLs."""
    search_url = "https://pixabay.com/api/"
    
    params = {
        'key': pixabay_api_key,
        'q': query,
        'image_type': 'all',
        'per_page': 3
    }
        
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()  # Raise an error for bad responses
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error occurred: {e}")  # Log the error
        return []  # Return an empty list on error
    except Exception as e:
        logging.error(f"An error occurred during the request: {e}")
        return []

    search_results = response.json()
    image_urls = [hit['largeImageURL'] for hit in search_results.get('hits', [])]  # Extract image URLs
    return image_urls[0]

