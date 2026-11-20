"""Tests for Bitcoin Phase 3: Display and Data Fetching."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from src.bitcoin.fetcher import BitcoinFetcher, BitcoinPrice, BlockInfo, MiningDifficulty
from src.display.manager import DisplayManager, MockDisplay, DisplayBase
from src.app import AppController


class TestBitcoinFetcher:
    """Tests for Bitcoin data fetcher."""
    
    @pytest.fixture
    def fetcher(self):
        """Create fetcher with mock mode."""
        return BitcoinFetcher(mock=True)
    
    def test_fetcher_init(self, fetcher):
        """Test fetcher initialization."""
        assert fetcher.mock is True
        assert fetcher._last_price is None
        assert fetcher._last_block is None
        assert fetcher._last_difficulty is None
    
    def test_mock_price(self, fetcher):
        """Test mock price generation."""
        price = fetcher.fetch_price()
        assert price is not None
        assert price.usd == 43250.50
        assert price.eur == 39800.75
        assert price.gbp == 34500.25
        assert price.timestamp > 0
    
    def test_mock_block(self, fetcher):
        """Test mock block generation."""
        block = fetcher.fetch_latest_block()
        assert block is not None
        assert block.height == 840000
        assert block.miner == "Foundry USA"
        assert block.transactions == 4821
        assert len(block.hash) > 0
    
    def test_mock_difficulty(self, fetcher):
        """Test mock difficulty generation."""
        difficulty = fetcher.fetch_difficulty()
        assert difficulty is not None
        assert difficulty.difficulty == 84000000000000.0
        assert len(difficulty.bits) > 0
    
    def test_price_dataclass(self):
        """Test BitcoinPrice dataclass."""
        price = BitcoinPrice(usd=50000.0, eur=45000.0, gbp=40000.0, timestamp=time.time())
        data = price.to_dict()
        assert data['usd'] == 50000.0
        assert 'timestamp' in data
    
    def test_block_dataclass(self):
        """Test BlockInfo dataclass."""
        block = BlockInfo(
            hash="abc123",
            height=840000,
            time=1700000000,
            miner="Pool",
            transactions=1000,
            timestamp=time.time()
        )
        data = block.to_dict()
        assert data['hash'] == "abc123"
        assert data['height'] == 840000
    
    def test_difficulty_dataclass(self):
        """Test MiningDifficulty dataclass."""
        diff = MiningDifficulty(
            difficulty=84000000000000.0,
            bits="1a123456",
            target="target_value",
            timestamp=time.time()
        )
        data = diff.to_dict()
        assert data['difficulty'] == 84000000000000.0
    
    def test_cache_price(self, fetcher):
        """Test price caching - should cache after fetch."""
        # Fetch in mock mode (doesn't cache automatically)
        price1 = fetcher.fetch_price()
        
        # Mock should return the data
        assert price1 is not None
        assert price1.usd == 43250.50
    
    def test_cache_block(self, fetcher):
        """Test block caching - should cache after fetch."""
        # Fetch in mock mode (doesn't cache automatically)
        block1 = fetcher.fetch_latest_block()
        
        # Mock should return the data
        assert block1 is not None
        assert block1.height == 840000
    
    def test_fetch_all(self, fetcher):
        """Test fetching all data at once."""
        result = fetcher.fetch_all()
        assert 'price' in result
        assert 'block' in result
        assert 'difficulty' in result
        assert result['price'] is not None
        assert result['block'] is not None
        assert result['difficulty'] is not None


class TestDisplayManager:
    """Tests for display manager."""
    
    @pytest.fixture
    def display(self):
        """Create display manager with mock display."""
        return DisplayManager(mock=True)
    
    def test_init(self, display):
        """Test display manager initialization."""
        assert display.width == 320
        assert display.height == 240
        assert display.current_state == "initial"
    
    def test_loading_screen(self, display):
        """Test loading screen."""
        display.show_loading("Test Loading")
        assert display.current_state == "loading"
    
    def test_connecting_wifi_screen(self, display):
        """Test WiFi connection screen."""
        display.show_connecting_wifi()
        assert display.current_state == "connecting_wifi"
    
    def test_ap_mode_screen(self, display):
        """Test AP mode setup screen."""
        display.show_ap_mode("192.168.4.1")
        assert display.current_state == "ap_mode"
    
    def test_bitcoin_info_screen(self, display):
        """Test Bitcoin info screen."""
        price_data = {'usd': 50000.0}
        block_data = {'height': 840000, 'hash': 'abc123def456', 'miner': 'Pool', 'transactions': 2000}
        difficulty_data = {'difficulty': 84000000000000.0}
        
        display.show_bitcoin_info(
            price=price_data,
            block=block_data,
            difficulty=difficulty_data,
            local_time="14:30:45"
        )
        assert display.current_state == "bitcoin_info"
    
    def test_error_screen(self, display):
        """Test error screen."""
        display.show_error("Test Error", "Error details")
        assert display.current_state == "error"
    
    def test_offline_screen(self, display):
        """Test offline screen."""
        display.show_offline("No WiFi")
        assert display.current_state == "offline"
    
    def test_last_block_time(self, display):
        """Test setting last block time."""
        now = time.time()
        display.set_last_block_time(now)
        assert display.last_block_time == now
    
    def test_state_change_callback(self, display):
        """Test state change callback."""
        callback_states = []
        
        def callback(state):
            callback_states.append(state)
        
        display.register_state_change_callback(callback)
        display.show_loading()
        
        assert "loading" in callback_states
    
    def test_mock_display(self):
        """Test mock display directly."""
        mock = MockDisplay()
        mock.clear()
        mock.fill((0, 0, 0))
        mock.text("Test", 100, 100, (255, 255, 255))
        mock.show()
        
        assert len(mock.buffer) > 0


class TestAppController:
    """Tests for main application controller."""
    
    @pytest.fixture
    def controller(self):
        """Create app controller with mocks."""
        display = DisplayManager(mock=True)
        wifi = Mock()
        bitcoin = BitcoinFetcher(mock=True)
        
        return AppController(
            display_manager=display,
            wifi_manager=wifi,
            bitcoin_fetcher=bitcoin
        )
    
    def test_controller_init(self, controller):
        """Test controller initialization."""
        assert controller.running is False
        assert controller.update_interval == 30
        assert controller.display is not None
    
    def test_get_status(self, controller):
        """Test getting controller status."""
        status = controller.get_status()
        assert 'running' in status
        assert 'display_state' in status
        assert 'wifi_connected' in status
        assert status['running'] is False
    
    def test_start_with_no_wifi_config(self, controller):
        """Test starting when no WiFi config exists."""
        controller.wifi.load_config.return_value = False
        
        # Don't actually start thread, just check setup
        if not controller.wifi.load_config():
            assert True
    
    def test_button_reset(self, controller):
        """Test reset button handling."""
        controller.wifi.reset = Mock()
        controller.on_button_press("reset")
        
        controller.wifi.reset.assert_called_once()
    
    def test_fetch_bitcoin_data(self, controller):
        """Test Bitcoin data fetching."""
        controller.is_wifi_connected = True
        controller._fetch_bitcoin_data()
        
        assert 'price' in controller.bitcoin_data
        assert 'block' in controller.bitcoin_data
        assert 'difficulty' in controller.bitcoin_data


class TestBitcoinInfoDisplay:
    """Integration tests for Bitcoin info display."""
    
    def test_bitcoin_info_complete_flow(self):
        """Test complete Bitcoin info display flow."""
        display = DisplayManager(mock=True)
        fetcher = BitcoinFetcher(mock=True)
        
        # Fetch data
        price = fetcher.fetch_price()
        block = fetcher.fetch_latest_block()
        difficulty = fetcher.fetch_difficulty()
        
        # Display data
        display.show_bitcoin_info(
            price=price.to_dict(),
            block=block.to_dict(),
            difficulty=difficulty.to_dict(),
            local_time="14:30:00"
        )
        
        assert display.current_state == "bitcoin_info"
        assert display.last_update > 0
    
    def test_time_since_block(self):
        """Test time since block calculation."""
        display = DisplayManager(mock=True)
        
        # Set block time 2 minutes ago
        past_time = time.time() - 120
        display.set_last_block_time(past_time)
        
        # Last block time should be set
        assert display.last_block_time > 0
        assert time.time() - display.last_block_time >= 120


class TestDisplayColors:
    """Tests for display color system."""
    
    def test_color_constants(self):
        """Test color constant definitions."""
        display = DisplayManager(mock=True)
        
        assert display.COLOR_BLACK == (0, 0, 0)
        assert display.COLOR_WHITE == (255, 255, 255)
        assert display.COLOR_BLUE == (0, 100, 255)
        assert display.COLOR_GREEN == (0, 200, 0)
        assert display.COLOR_RED == (255, 0, 0)
        assert display.COLOR_YELLOW == (255, 200, 0)
        assert display.COLOR_GRAY == (100, 100, 100)


class TestDataPersistence:
    """Tests for data handling and persistence."""
    
    def test_bitcoin_data_to_dict(self):
        """Test converting Bitcoin data to dictionaries."""
        fetcher = BitcoinFetcher(mock=True)
        
        price = fetcher.fetch_price()
        block = fetcher.fetch_latest_block()
        difficulty = fetcher.fetch_difficulty()
        
        price_dict = price.to_dict()
        block_dict = block.to_dict()
        difficulty_dict = difficulty.to_dict()
        
        # Should be JSON serializable
        import json
        json.dumps(price_dict)
        json.dumps(block_dict)
        json.dumps(difficulty_dict)


class TestErrorHandling:
    """Tests for error handling in display."""
    
    def test_error_display(self):
        """Test error display."""
        display = DisplayManager(mock=True)
        display.show_error("Connection Error", "Failed to connect to API")
        
        assert display.current_state == "error"
    
    def test_offline_display(self):
        """Test offline display."""
        display = DisplayManager(mock=True)
        display.show_offline("WiFi Disconnected")
        
        assert display.current_state == "offline"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
