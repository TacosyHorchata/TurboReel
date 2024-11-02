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
    response = requests.get(image_url, timeout=15)
    #save the image to the assets folder
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'images')
    os.makedirs(assets_dir, exist_ok=True)
    image_path = os.path.join(assets_dir, f"{uuid.uuid4()}.jpg")
    with open(image_path, 'wb') as f:
        f.write(response.content)
    
    logging.info(f"Downloaded image to: {image_path}")
    return image_path

def generate_image_pollinations(query, width=540, height=960, model=None, seed=None, nologo=False, private=True, enhance=False, timeout=30):
    """Generate an image using Pollinations AI API
    
    Args:
        query (str): Text description of the image to generate
        width (int, optional): Width of generated image. Defaults to 1024
        height (int, optional): Height of generated image. Defaults to 1024
        model (str, optional): Model to use for generation
        seed (int, optional): Seed for reproducible results
        nologo (bool, optional): Turn off logo rendering. Defaults to False
        private (bool, optional): Prevent image from appearing in public feed. Defaults to True
        enhance (bool, optional): Enable prompt enhancing via LLM. Defaults to False
        timeout (int, optional): Maximum time to wait for image generation in seconds. Defaults to 30
    
    Returns:
        list: List containing the generated image URL if successful, empty list otherwise
    """
    try:
        # Build query parameters
        params = {
            'width': width,
            'height': height,
            'nologo': str(nologo).lower(),
            'private': str(private).lower(),
            'enhance': str(enhance).lower()
        }
        if model:
            params['model'] = model
        if seed is not None:
            params['seed'] = seed

        # URL encode the prompt
        encoded_query = requests.utils.quote(query)
        generate_url = f"https://image.pollinations.ai/prompt/{encoded_query}"

        full_url = requests.Request('GET', generate_url, params=params).prepare().url
        response = requests.get(full_url, timeout=timeout)
        
        if response.status_code == 200:
            # Validate URL before returning
            if not full_url.startswith(('http://', 'https://')):
                logging.error(f"Invalid URL generated: {full_url}")
                return []
            return [full_url]
        
        logging.error(f"Failed to generate image. Status code: {response.status_code}")
        return []
        
    except requests.exceptions.Timeout:
        logging.error(f"Timeout occurred while generating image: {full_url}")
        return []

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

