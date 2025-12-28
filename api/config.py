"""Configuration module for loading environment variables."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for API keys and settings."""

    # Google Custom Search API
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    GOOGLE_SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID', '')

    # Bing Search API
    BING_API_KEY = os.getenv('BING_API_KEY', '')
    BING_SEARCH_ENDPOINT = os.getenv(
        'BING_SEARCH_ENDPOINT',
        'https://api.bing.microsoft.com/v7.0/search'
    )

    # Google Maps API
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')

    # OpenAI API (LLM reasoning layer)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '60'))

    @staticmethod
    def validate_config():
        """Validate that required (non-optional) API keys are set."""
        missing_keys = []

        if not Config.GOOGLE_API_KEY or Config.GOOGLE_API_KEY == 'your_google_api_key_here':
            missing_keys.append('GOOGLE_API_KEY')

        if not Config.GOOGLE_SEARCH_ENGINE_ID or Config.GOOGLE_SEARCH_ENGINE_ID == 'your_search_engine_id_here':
            missing_keys.append('GOOGLE_SEARCH_ENGINE_ID')

        if not Config.BING_API_KEY or Config.BING_API_KEY == 'your_bing_api_key_here':
            missing_keys.append('BING_API_KEY')

        if not Config.GOOGLE_MAPS_API_KEY or Config.GOOGLE_MAPS_API_KEY == 'your_google_maps_api_key_here':
            missing_keys.append('GOOGLE_MAPS_API_KEY')

        # NOTE: OPENAI_API_KEY intentionally NOT required
        return missing_keys



# """Configuration module for loading environment variables."""
# import os
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()


# class Config:
#     """Configuration class for API keys and settings."""
    
#     # Google Custom Search API
#     GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
#     GOOGLE_SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID', '')
    
#     # Bing Search API
#     BING_API_KEY = os.getenv('BING_API_KEY', '')
#     BING_SEARCH_ENDPOINT = os.getenv('BING_SEARCH_ENDPOINT', 'https://api.bing.microsoft.com/v7.0/search')
    
#     # Google Maps API
#     GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')
    
#     # Rate limiting
#     MAX_REQUESTS_PER_MINUTE = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '60'))
    
#     @staticmethod
#     def validate_config():
#         """Validate that required API keys are set."""
#         missing_keys = []
        
#         if not Config.GOOGLE_API_KEY or Config.GOOGLE_API_KEY == 'your_google_api_key_here':
#             missing_keys.append('GOOGLE_API_KEY')
#         if not Config.GOOGLE_SEARCH_ENGINE_ID or Config.GOOGLE_SEARCH_ENGINE_ID == 'your_search_engine_id_here':
#             missing_keys.append('GOOGLE_SEARCH_ENGINE_ID')
#         if not Config.BING_API_KEY or Config.BING_API_KEY == 'your_bing_api_key_here':
#             missing_keys.append('BING_API_KEY')
#         if not Config.GOOGLE_MAPS_API_KEY or Config.GOOGLE_MAPS_API_KEY == 'your_google_maps_api_key_here':
#             missing_keys.append('GOOGLE_MAPS_API_KEY')
        
#         return missing_keys


