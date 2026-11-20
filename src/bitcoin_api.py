"""
Bitcoin API Data Fetcher

Handles all API calls to fetch Bitcoin price, block info, and difficulty.
Includes caching, retry logic, and graceful error handling.

Data sources:
- mempool.space: Bitcoin USD price and block information
"""

import time
import json
import sys


class APICache:
    """Simple cache with TTL (time-to-live) support."""
    
    def __init__(self, ttl_seconds=60):
        self.data = {}
        self.timestamps = {}
        self.ttl = ttl_seconds
    
    def get(self, key):
        """Get cached value if still valid."""
        if key not in self.data:
            return None
        
        age = time.time() - self.timestamps[key]
        if age < self.ttl:
            return self.data[key]
        
        # Cache expired
        del self.data[key]
        del self.timestamps[key]
        return None
    
    def set(self, key, value):
        """Store value with current timestamp."""
        self.data[key] = value
        self.timestamps[key] = time.time()
    
    def clear(self):
        """Clear all cached data."""
        self.data.clear()
        self.timestamps.clear()


class BitcoinAPI:
    """
    Fetch Bitcoin data from public APIs.
    
    Usage:
        api = BitcoinAPI()
        price = api.get_price()      # Returns {'usd': 45320.50}
        block = api.get_block()      # Returns block info dict
        difficulty = api.get_difficulty()  # Returns difficulty value
    """
    
    def __init__(self, use_mock_data=False, timeout=5):
        self.use_mock_data = use_mock_data
        self.timeout = timeout
        
        # Initialize caches with different TTLs
        self.cache_price = APICache(ttl_seconds=60)      # Cache price for 60s
        self.cache_block = APICache(ttl_seconds=60)      # Cache block for 60s
        self.cache_difficulty = APICache(ttl_seconds=300)  # Cache difficulty for 5min
        
        # Last known values (for fallback when APIs fail)
        self.last_price = None
        self.last_block = None
        self.last_difficulty = None
        self.price_updated_at = None
        self.block_updated_at = None
        self.price_fresh = None
        self.block_fresh = None
        
        # API endpoints
        self.url_price = "https://mempool.space/api/v1/prices"
        self.url_latest_block = "https://mempool.space/api/blocks/tip/hash"
        self.url_block = "https://mempool.space/api/block/"
    
    def _fetch_url(self, url, params=None, retries=3, as_text=False):
        """
        Fetch URL with retry logic and exponential backoff.
        
        Args:
            url: URL to fetch
            params: Query parameters dict
            retries: Number of retry attempts
        
        Returns:
            Response dict or None if all retries fail
        """
        try:
            import requests
        except ImportError as e:
            print(f"HTTP client unavailable: {e}")
            return None

        micropython = sys.implementation.name == 'micropython'
        errors = (OSError, ValueError)
        if not micropython:
            errors += (requests.exceptions.RequestException,)

        full_url = url
        if micropython and params:
            query = "&".join(f"{key}={value}" for key, value in params.items())
            full_url = f"{url}?{query}"

        for attempt in range(retries):
            response = None
            try:
                if micropython:
                    import gc
                    gc.collect()
                    response = requests.get(full_url, timeout=self.timeout)
                else:
                    response = requests.get(url, params=params, timeout=self.timeout)
                if response.status_code == 200:
                    return response.text if as_text else response.json()
                print(f"HTTP {response.status_code} fetching {url}")
                if response.status_code != 429:
                    return None
            except errors as e:
                print(f"Error fetching {url}: {e}")
            finally:
                if response is not None:
                    response.close()
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

        return None
    
    def get_price(self):
        """
        Fetch current Bitcoin price.
        
        Returns:
            {'usd': 45320.50} or None
            Returns cached value if available and fresh
        """
        # Check cache first
        cached = self.cache_price.get('price')
        if cached is not None:
            return cached
        
        # Use mock data for testing
        if self.use_mock_data:
            price = {'usd': 45320.50}
            self.last_price = price
            self.price_updated_at = time.time()
            self.price_fresh = True
            return price
        
        # Fetch from API
        response = self._fetch_url(self.url_price)

        if response and response.get('USD') is not None:
            price = {'usd': response['USD']}
            self.cache_price.set('price', price)
            self.last_price = price
            self.price_updated_at = time.time()
            self.price_fresh = True
            return price
        
        # Return last known value on failure
        self.price_fresh = False
        return self.last_price
    
    def get_block(self):
        """
        Fetch current/latest block information.
        
        Returns:
            {
                'height': 863452,
                'hash': '0a3f7e2c...',
                'time': 1700500000,
                'n_tx': 2847,
                'size': 1245000,
                'mrkl_root': '5a3f7e2c...',
                'prev_block_hash': '9b4e6d1f...',
            }
            Or None if fetch fails
        """
        # Check cache first
        cached = self.cache_block.get('block')
        if cached is not None:
            return cached
        
        # Use mock data for testing
        if self.use_mock_data:
            block = {
                'height': 863452,
                'hash': '0a3f7e2c1b4a8f9e3d5c6b7a8f9e0d1c2b3a4f5e6d7c8b9a0e1d2f3c4a5b6',
                'time': 1700500000,
                'n_tx': 2847,
                'size': 1245000,
                'mrkl_root': '5a3f7e2c1b4a8f9e3d5c6b7a8f9e0d1c2b3a4f5e6d7c8b9a0e1d2f3c4a5b6',
                'prev_block_hash': '9b4e6d1f2e3c4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f',
            }
            self.last_block = block
            self.block_updated_at = time.time()
            self.block_fresh = True
            return block
        
        # Fetch from API
        block_hash = self._fetch_url(self.url_latest_block, as_text=True)
        response = self._fetch_url(self.url_block + block_hash.strip()) if block_hash else None
        
        if response:
            # Extract relevant fields
            block = {
                'height': response.get('height'),
                'hash': response.get('id'),
                'time': response.get('timestamp'),
                'n_tx': response.get('tx_count'),
                'size': response.get('size'),
                'mrkl_root': response.get('merkle_root'),
                'prev_block_hash': response.get('previousblockhash'),
            }
            difficulty = response.get('difficulty')
            if difficulty is not None:
                self.cache_difficulty.set('difficulty', difficulty)
                self.last_difficulty = difficulty
            self.cache_block.set('block', block)
            self.last_block = block
            self.block_updated_at = time.time()
            self.block_fresh = block['height'] is not None and difficulty is not None
            return block
        
        # Return last known value on failure
        self.block_fresh = False
        return self.last_block
    
    def get_difficulty(self):
        """
        Fetch current Bitcoin network difficulty.
        
        Returns:
            difficulty value (float) or None
        """
        # Check cache first
        cached = self.cache_difficulty.get('difficulty')
        if cached is not None:
            return cached
        
        # Use mock data for testing
        if self.use_mock_data:
            difficulty = 84.2e12  # 84.2 trillion
            self.last_difficulty = difficulty
            return difficulty
        
        self.get_block()
        return self.last_difficulty
    
    def get_all_data(self):
        """
        Fetch all data at once.
        
        Returns:
            {
                'price': {'usd': ...},
                'block': {...},
                'difficulty': ...,
                'timestamp': <fetch_time>
            }
        """
        return {
            'price': self.get_price(),
            'block': self.get_block(),
            'difficulty': self.get_difficulty(),
            'timestamp': time.time(),
        }
    
    def clear_cache(self):
        """Clear all cached data (force fresh fetch on next call)."""
        self.cache_price.clear()
        self.cache_block.clear()
        self.cache_difficulty.clear()


# For testing purposes
if __name__ == '__main__':
    print("Bitcoin API Test")
    print("=" * 60)
    
    # Test with mock data first
    print("\n1. Testing with MOCK data:")
    api_mock = BitcoinAPI(use_mock_data=True)
    
    price = api_mock.get_price()
    print(f"Price: ${price['usd']} USD")
    
    block = api_mock.get_block()
    print(f"Block: #{block['height']}")
    print(f"Hash: {block['hash']}")
    
    difficulty = api_mock.get_difficulty()
    print(f"Difficulty: {difficulty:.2e}")
    
    # Test with real APIs (requires internet)
    print("\n2. Testing with REAL APIs (may fail without internet):")
    api_real = BitcoinAPI(use_mock_data=False)
    
    try:
        price = api_real.get_price()
        if price:
            print(f"Price: ${price['usd']} USD")
        else:
            print("Price: Failed to fetch (using last known or None)")
    except Exception as e:
        print(f"Price: Error - {e}")
    
    try:
        block = api_real.get_block()
        if block:
            print(f"Block: #{block['height']}")
            print(f"Hash: {block['hash'][:16]}...")
        else:
            print("Block: Failed to fetch")
    except Exception as e:
        print(f"Block: Error - {e}")
    
    try:
        difficulty = api_real.get_difficulty()
        if difficulty:
            print(f"Difficulty: {difficulty:.2e}")
        else:
            print("Difficulty: Failed to fetch")
    except Exception as e:
        print(f"Difficulty: Error - {e}")
    
    print("\n3. Testing cache (should return cached values immediately):")
    start = time.time()
    price2 = api_real.get_price()
    elapsed = time.time() - start
    print(f"Second price fetch took {elapsed*1000:.1f}ms (should be <1ms if cached)")
