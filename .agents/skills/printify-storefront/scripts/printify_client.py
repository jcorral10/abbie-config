import os
import json
import time
import logging
import requests
import argparse
from typing import List, Dict, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('printify_client')

class PrintifyAPIError(Exception):
    """Custom exception for Printify API errors."""
    pass

class PrintifyClient:
    BASE_URL = "https://api.printify.com/v1"
    
    def __init__(self, api_token: str, shop_id: Optional[str] = None):
        self.api_token = api_token
        self.shop_id = shop_id
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json;charset=utf-8"
        })
        self.req_count = 0
        self.window_start = time.time()
        
    def _rate_limit(self):
        """Simple sliding window rate limiter (600 req/min)."""
        self.req_count += 1
        now = time.time()
        if now - self.window_start > 60:
            self.req_count = 1
            self.window_start = now
        elif self.req_count > 580:  # Buffer for safety
            sleep_time = 60 - (now - self.window_start)
            if sleep_time > 0:
                logger.warning(f"Rate limit approaching. Sleeping for {sleep_time:.2f} seconds.")
                time.sleep(sleep_time)
            self.req_count = 0
            self.window_start = time.time()
            
    def _request(self, method: str, endpoint: str, max_retries: int = 3, **kwargs) -> dict:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        for attempt in range(max_retries):
            self._rate_limit()
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Handle specific HTTP error codes
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    logger.warning(f"429 Too Many Requests. Retrying in {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                    
                response.raise_for_status()
                
                # Check for empty response (e.g. DELETE)
                if not response.content:
                    return {}
                    
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                if status_code >= 500 and attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Server error {status_code}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                logger.error(f"HTTP Error {status_code}: {e.response.text}")
                raise PrintifyAPIError(f"API request failed: {e.response.text}") from e
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise PrintifyAPIError(f"Network error: {e}") from e
                
        raise PrintifyAPIError("Max retries exceeded")

    def get_shops(self) -> list:
        """GET /v1/shops.json"""
        return self._request("GET", "shops.json")
    
    def upload_image(self, file_name: str, url: str = None, base64_contents: str = None) -> dict:
        """POST /v1/uploads/images.json"""
        data = {"file_name": file_name}
        if url:
            data["url"] = url
        elif base64_contents:
            data["contents"] = base64_contents
        else:
            raise ValueError("Must provide either url or base64_contents")
        return self._request("POST", "uploads/images.json", json=data)
    
    def list_blueprints(self) -> list:
        """GET /v1/catalog/blueprints.json"""
        return self._request("GET", "catalog/blueprints.json")
    
    def get_blueprint(self, blueprint_id: int) -> dict:
        """GET /v1/catalog/blueprints/{id}.json"""
        return self._request("GET", f"catalog/blueprints/{blueprint_id}.json")
    
    def get_print_providers(self, blueprint_id: int) -> list:
        """GET /v1/catalog/blueprints/{id}/print_providers.json"""
        return self._request("GET", f"catalog/blueprints/{blueprint_id}/print_providers.json")
    
    def get_variants(self, blueprint_id: int, print_provider_id: int) -> dict:
        """GET /v1/catalog/blueprints/{id}/print_providers/{id}/variants.json"""
        return self._request("GET", f"catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/variants.json")
    
    def get_shipping(self, blueprint_id: int, print_provider_id: int) -> dict:
        """GET /v1/catalog/blueprints/{id}/print_providers/{id}/shipping.json"""
        return self._request("GET", f"catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/shipping.json")
    
    def create_product(self, title: str, description: str, tags: list, blueprint_id: int, 
                       print_provider_id: int, variants: list, print_areas: list, **kwargs) -> dict:
        """POST /v1/shops/{shop_id}/products.json"""
        if not self.shop_id:
            raise ValueError("shop_id must be set to create products")
            
        data = {
            "title": title,
            "description": description,
            "blueprint_id": blueprint_id,
            "print_provider_id": print_provider_id,
            "variants": variants,
            "print_areas": print_areas,
            "tags": tags
        }
        data.update(kwargs)
        return self._request("POST", f"shops/{self.shop_id}/products.json", json=data)
    
    def get_product(self, product_id: str) -> dict:
        """GET /v1/shops/{shop_id}/products/{product_id}.json"""
        if not self.shop_id:
            raise ValueError("shop_id must be set")
        return self._request("GET", f"shops/{self.shop_id}/products/{product_id}.json")
    
    def update_product(self, product_id: str, data: dict) -> dict:
        """PUT /v1/shops/{shop_id}/products/{product_id}.json"""
        if not self.shop_id:
            raise ValueError("shop_id must be set")
        return self._request("PUT", f"shops/{self.shop_id}/products/{product_id}.json", json=data)
    
    def delete_product(self, product_id: str) -> dict:
        """DELETE /v1/shops/{shop_id}/products/{product_id}.json"""
        if not self.shop_id:
            raise ValueError("shop_id must be set")
        return self._request("DELETE", f"shops/{self.shop_id}/products/{product_id}.json")
    
    def publish_product(self, product_id: str) -> dict:
        """POST /v1/shops/{shop_id}/products/{product_id}/publish.json"""
        if not self.shop_id:
            raise ValueError("shop_id must be set")
        # Empty payload as required by some publish endpoints, or update as needed
        data = {"title": True, "description": True, "images": True, "variants": True, "tags": True}
        return self._request("POST", f"shops/{self.shop_id}/products/{product_id}/publish.json", json=data)
    
    def unpublish_product(self, product_id: str) -> dict:
        """POST /v1/shops/{shop_id}/products/{product_id}/unpublish.json"""
        if not self.shop_id:
            raise ValueError("shop_id must be set")
        return self._request("POST", f"shops/{self.shop_id}/products/{product_id}/unpublish.json")
    
    def list_products(self, page: int = 1, limit: int = 20) -> dict:
        """GET /v1/shops/{shop_id}/products.json"""
        if not self.shop_id:
            raise ValueError("shop_id must be set")
        params = {"page": page, "limit": limit}
        return self._request("GET", f"shops/{self.shop_id}/products.json", params=params)
    
    def get_orders(self, page: int = 1, limit: int = 20) -> dict:
        """GET /v1/shops/{shop_id}/orders.json"""
        if not self.shop_id:
            raise ValueError("shop_id must be set")
        params = {"page": page, "limit": limit}
        return self._request("GET", f"shops/{self.shop_id}/orders.json", params=params)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Printify API Client")
    parser.add_argument("--test", action="store_true", help="Run basic connection tests")
    args = parser.parse_args()
    
    if args.test:
        token = os.environ.get("PRINTIFY_API_TOKEN")
        if not token:
            logger.error("PRINTIFY_API_TOKEN environment variable is not set")
            exit(1)
            
        try:
            client = PrintifyClient(api_token=token)
            logger.info("Fetching shops...")
            shops = client.get_shops()
            logger.info(f"Found {len(shops)} shops.")
            for shop in shops:
                logger.info(f"- Shop ID: {shop.get('id')} | Title: {shop.get('title')}")
                
            logger.info("Fetching blueprints (limit 5 for test)...")
            blueprints = client.list_blueprints()
            for bp in blueprints[:5]:
                logger.info(f"- Blueprint ID: {bp.get('id')} | Name: {bp.get('title')}")
                
            logger.info("Test completed successfully.")
        except Exception as e:
            logger.error(f"Test failed: {e}")
            exit(1)
