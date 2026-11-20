"""Bitcoin data fetcher - retrieves current price, block info, and difficulty."""

import json
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class BitcoinPrice:
    """Bitcoin price data."""
    usd: float
    eur: float
    gbp: float
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BlockInfo:
    """Bitcoin block information."""
    hash: str
    height: int
    time: int
    miner: str
    transactions: int
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MiningDifficulty:
    """Bitcoin mining difficulty."""
    difficulty: float
    bits: str
    target: str
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BitcoinFetcher:
    """Fetches Bitcoin data from public APIs."""
    
    # CoinGecko API endpoints (free, no auth required)
    PRICE_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,eur,gbp"
    MEMPOOL_API = "https://mempool.space/api/blocks/tip/height"
    MEMPOOL_BLOCK_URL = "https://mempool.space/api/block/{hash}"
    MEMPOOL_DIFFICULTY = "https://mempool.space/api/difficulty-adjustment"
    
    def __init__(self, mock: bool = False):
        """
        Initialize Bitcoin fetcher.
        
        Args:
            mock: If True, return mock data (for testing without network)
        """
        self.mock = mock
        self._last_price: Optional[BitcoinPrice] = None
        self._last_block: Optional[BlockInfo] = None
        self._last_difficulty: Optional[MiningDifficulty] = None
        self._fetch_timeout = 10  # seconds
        
    def set_mock(self, enabled: bool):
        """Enable/disable mock mode for testing."""
        self.mock = enabled
        
    def fetch_price(self) -> Optional[BitcoinPrice]:
        """
        Fetch current Bitcoin price.
        
        Returns:
            BitcoinPrice object or None if fetch fails
        """
        if self.mock:
            return self._mock_price()
            
        try:
            import urequests as requests
        except ImportError:
            try:
                import requests
            except ImportError:
                return self._get_cached_price()
        
        try:
            response = requests.get(self.PRICE_URL, timeout=self._fetch_timeout)
            if response.status_code == 200:
                data = response.json()
                bitcoin_data = data.get('bitcoin', {})
                self._last_price = BitcoinPrice(
                    usd=bitcoin_data.get('usd', 0.0),
                    eur=bitcoin_data.get('eur', 0.0),
                    gbp=bitcoin_data.get('gbp', 0.0),
                    timestamp=time.time()
                )
                return self._last_price
        except Exception as e:
            print(f"Error fetching price: {e}")
        
        return self._get_cached_price()
    
    def fetch_latest_block(self) -> Optional[BlockInfo]:
        """
        Fetch latest Bitcoin block information.
        
        Returns:
            BlockInfo object or None if fetch fails
        """
        if self.mock:
            return self._mock_block()
        
        try:
            import urequests as requests
        except ImportError:
            try:
                import requests
            except ImportError:
                return self._get_cached_block()
        
        try:
            # First get the latest block height
            height_response = requests.get(self.MEMPOOL_API, timeout=self._fetch_timeout)
            if height_response.status_code != 200:
                return self._get_cached_block()
            
            height = height_response.json()
            
            # Get block details
            block_url = f"https://mempool.space/api/block-height/{height}"
            block_response = requests.get(block_url, timeout=self._fetch_timeout)
            if block_response.status_code != 200:
                return self._get_cached_block()
            
            block_hash = block_response.json()
            
            # Get full block details
            details_url = self.MEMPOOL_BLOCK_URL.format(hash=block_hash)
            details_response = requests.get(details_url, timeout=self._fetch_timeout)
            if details_response.status_code != 200:
                return self._get_cached_block()
            
            details = details_response.json()
            self._last_block = BlockInfo(
                hash=details.get('id', 'unknown'),
                height=details.get('height', 0),
                time=details.get('timestamp', 0),
                miner=details.get('extras', {}).get('pool', {}).get('name', 'Unknown'),
                transactions=details.get('tx_count', 0),
                timestamp=time.time()
            )
            return self._last_block
            
        except Exception as e:
            print(f"Error fetching block: {e}")
        
        return self._get_cached_block()
    
    def fetch_difficulty(self) -> Optional[MiningDifficulty]:
        """
        Fetch current Bitcoin mining difficulty.
        
        Returns:
            MiningDifficulty object or None if fetch fails
        """
        if self.mock:
            return self._mock_difficulty()
        
        try:
            import urequests as requests
        except ImportError:
            try:
                import requests
            except ImportError:
                return self._get_cached_difficulty()
        
        try:
            response = requests.get(self.MEMPOOL_DIFFICULTY, timeout=self._fetch_timeout)
            if response.status_code == 200:
                data = response.json()
                self._last_difficulty = MiningDifficulty(
                    difficulty=data.get('difficulty', 0.0),
                    bits=data.get('bits', ''),
                    target=data.get('target', ''),
                    timestamp=time.time()
                )
                return self._last_difficulty
        except Exception as e:
            print(f"Error fetching difficulty: {e}")
        
        return self._get_cached_difficulty()
    
    def fetch_all(self) -> Dict[str, Any]:
        """
        Fetch all Bitcoin data at once.
        
        Returns:
            Dictionary with price, block, and difficulty data
        """
        return {
            'price': self.fetch_price(),
            'block': self.fetch_latest_block(),
            'difficulty': self.fetch_difficulty()
        }
    
    def _get_cached_price(self) -> Optional[BitcoinPrice]:
        """Get last cached price or return None."""
        return self._last_price
    
    def _get_cached_block(self) -> Optional[BlockInfo]:
        """Get last cached block or return None."""
        return self._last_block
    
    def _get_cached_difficulty(self) -> Optional[MiningDifficulty]:
        """Get last cached difficulty or return None."""
        return self._last_difficulty
    
    def _mock_price(self) -> BitcoinPrice:
        """Generate mock price data."""
        return BitcoinPrice(
            usd=43250.50,
            eur=39800.75,
            gbp=34500.25,
            timestamp=time.time()
        )
    
    def _mock_block(self) -> BlockInfo:
        """Generate mock block data."""
        return BlockInfo(
            hash="000000000000000000039cbb3e0f1a8c5f5c5d5e5f5a5b5c5d5e5f5a5b5c5d",
            height=840000,
            time=1700000000,
            miner="Foundry USA",
            transactions=4821,
            timestamp=time.time()
        )
    
    def _mock_difficulty(self) -> MiningDifficulty:
        """Generate mock difficulty data."""
        return MiningDifficulty(
            difficulty=84000000000000.0,
            bits="1a123456",
            target="00000000000000000003123456789abcdef",
            timestamp=time.time()
        )
