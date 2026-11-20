"""
Unit Tests for Bitcoin API

Tests bitcoin_api.py with mock data and simulated responses.

Run with: pytest tests/test_bitcoin_api.py
"""

import sys
import os
import time
from unittest.mock import Mock

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bitcoin_api import BitcoinAPI, APICache
import main as app_main
import utils
from utils import (
    format_sast_time, format_time_ago, format_time_delta,
    format_number, format_price, format_hash, format_difficulty
)


@pytest.mark.parametrize(
    "platform, args, expected_mock",
    [
        ("esp32", [], False),
        ("esp32", ["--mock"], True),
        ("win32", [], True),
        ("win32", ["--display"], False),
    ],
)
def test_main_display_selection(monkeypatch, platform, args, expected_mock):
    app_class = Mock()
    monkeypatch.setattr(app_main, 'BitcoinApp', app_class)
    monkeypatch.setattr(app_main, 'setup_wifi', Mock())
    monkeypatch.setattr(app_main.sys, 'platform', platform)
    monkeypatch.setattr(app_main.sys, 'argv', ['main.py'] + args)

    app_main.main()

    assert app_class.call_args.kwargs['mock_display'] is expected_mock
    app_class.return_value.run.assert_called_once_with(duration=None)
    if platform == 'esp32' and not expected_mock:
        app_class.return_value._render_display.assert_called_once_with()
    else:
        app_class.return_value._render_display.assert_not_called()


def test_micropython_http_query_and_response_closed(monkeypatch):
    class Response:
        status_code = 200
        closed = False

        def json(self):
            return {'bitcoin': {'usd': 123}}

        def close(self):
            self.closed = True

    response = Response()
    requests = Mock()
    requests.get.return_value = response
    monkeypatch.setitem(sys.modules, 'requests', requests)
    monkeypatch.setattr(app_main.sys, 'implementation', Mock(name='micropython'))
    app_main.sys.implementation.name = 'micropython'
    api = BitcoinAPI(use_mock_data=False)

    assert api._fetch_url('https://example.test', params={'ids': 'bitcoin'}) == {
        'bitcoin': {'usd': 123}
    }
    requests.get.assert_called_once_with(
        'https://example.test?ids=bitcoin', timeout=5,
    )
    assert response.closed


def test_live_price_and_block_mapping(monkeypatch):
    api = BitcoinAPI(use_mock_data=False)
    responses = {
        api.url_price: {'USD': 50000},
        api.url_latest_block: 'abc',
        api.url_block + 'abc': {
            'id': 'abc', 'height': 123, 'timestamp': 1700000000,
            'tx_count': 42, 'difficulty': 84000000000000,
        },
    }
    fetch = Mock(side_effect=lambda url, **kwargs: responses[url])
    monkeypatch.setattr(api, '_fetch_url', fetch)

    assert api.get_price() == {'usd': 50000}
    assert api.get_block()['n_tx'] == 42
    assert api.last_block['hash'] == 'abc'
    assert api.get_difficulty() == 84000000000000
    assert fetch.call_count == 3


def test_failed_fetch_marks_cached_price_stale(monkeypatch):
    api = BitcoinAPI(use_mock_data=False)
    fetch = Mock(side_effect=[{'USD': 50000}, None])
    monkeypatch.setattr(api, '_fetch_url', fetch)

    price = api.get_price()
    updated = api.price_updated_at
    api.cache_price.clear()

    assert api.get_price() == price
    assert api.price_fresh is False
    assert api.price_updated_at == updated


class TestAPICache:
    """Test APICache functionality."""
    
    def test_cache_set_and_get(self):
        """Test basic cache set/get."""
        cache = APICache(ttl_seconds=10)
        cache.set('test_key', 'test_value')
        
        assert cache.get('test_key') == 'test_value'
    
    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = APICache(ttl_seconds=1)
        cache.set('test_key', 'test_value')
        
        # Should be in cache
        assert cache.get('test_key') == 'test_value'
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get('test_key') is None
    
    def test_cache_missing_key(self):
        """Test getting non-existent key."""
        cache = APICache(ttl_seconds=10)
        assert cache.get('nonexistent') is None
    
    def test_cache_clear(self):
        """Test clearing cache."""
        cache = APICache(ttl_seconds=10)
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        
        cache.clear()
        
        assert cache.get('key1') is None
        assert cache.get('key2') is None


class TestBitcoinAPIMock:
    """Test BitcoinAPI with mock data."""
    
    def test_mock_price(self):
        """Test fetching price with mock data."""
        api = BitcoinAPI(use_mock_data=True)
        price = api.get_price()
        
        assert price is not None
        assert 'usd' in price
        assert price['usd'] == 45320.50
        assert 'zar' not in price
    
    def test_mock_block(self):
        """Test fetching block with mock data."""
        api = BitcoinAPI(use_mock_data=True)
        block = api.get_block()
        
        assert block is not None
        assert 'height' in block
        assert 'hash' in block
        assert 'time' in block
        assert block['height'] == 863452
    
    def test_mock_difficulty(self):
        """Test fetching difficulty with mock data."""
        api = BitcoinAPI(use_mock_data=True)
        difficulty = api.get_difficulty()
        
        assert difficulty is not None
        assert difficulty == 84.2e12
    
    def test_cache_working(self):
        """Test that caching is working."""
        api = BitcoinAPI(use_mock_data=True)
        
        # First fetch
        price1 = api.get_price()
        
        # Modify the mock data to verify cache is used
        api.cache_price.set('price', {'usd': 99999})
        
        # Second fetch should return cached (modified) data
        price2 = api.get_price()
        
        assert price2['usd'] == 99999  # From cache
    
    def test_get_all_data(self):
        """Test fetching all data at once."""
        api = BitcoinAPI(use_mock_data=True)
        data = api.get_all_data()
        
        assert 'price' in data
        assert 'block' in data
        assert 'difficulty' in data
        assert 'timestamp' in data
    
    def test_clear_cache(self):
        """Test clearing cache."""
        api = BitcoinAPI(use_mock_data=True)
        
        # Fetch data (cached)
        price1 = api.get_price()
        
        # Clear cache
        api.clear_cache()
        
        # Next fetch should recompute (or fetch again)
        # For mock, it will return mock data again
        price2 = api.get_price()
        
        assert price2 is not None


class TestFormatting:
    """Test utility formatting functions."""

    def test_sast_unix_timestamp(self):
        assert utils.format_sast_time(1700000000) == "00:13"
        assert utils.format_sast_time_full(1700000000) == "00:13:20"

    def test_micropython_epoch(self, monkeypatch):
        offset = 946684800
        real_gmtime = time.gmtime
        monkeypatch.setattr(utils, '_UNIX_EPOCH_OFFSET', offset)
        monkeypatch.setattr(utils.time, 'time', lambda: 1700000150 - offset)
        monkeypatch.setattr(utils.time, 'gmtime', lambda value: real_gmtime(value + offset))

        assert utils.format_sast_time(1700000000) == "00:13"
        assert utils.format_sast_time_full() == "00:15:50"
        assert utils.format_time_ago(1700000000) == "2 min 30 sec ago"
        assert utils.seconds_since_block(1700000000) == 150
    
    def test_format_time_ago(self):
        """Test time ago formatting."""
        # 2.5 minutes ago
        old_time = time.time() - 150
        result = format_time_ago(old_time)
        
        assert "ago" in result
        assert "2 min" in result or "150" in result
    
    def test_format_time_delta(self):
        """Test time delta formatting."""
        # 2 minutes 34 seconds
        result = format_time_delta(154)
        
        assert result == "2:34"
    
    def test_format_time_delta_hours(self):
        """Test time delta with hours."""
        # 1 hour, 2 minutes, 30 seconds
        result = format_time_delta(3750)
        
        assert result == "1:02:30"
    
    def test_format_number_trillion(self):
        """Test formatting large numbers."""
        result = format_number(84.2e12, decimals=1)
        
        assert result == "84.2T"
    
    def test_format_number_million(self):
        """Test formatting millions."""
        result = format_number(1234567, decimals=1)
        
        assert result == "1.2M"
    
    def test_format_price(self):
        """Test price formatting."""
        assert format_price(45320.50) == "$45 320.50"
        assert format_price(999.99) == "$999.99"
        assert format_price(1234567.89) == "$1 234 567.89"
        assert format_price(-1234.50) == "$-1 234.50"
    
    def test_format_hash(self):
        """Test hash formatting."""
        full_hash = "0a3f7e2c1b4a8f9e3d5c6b7a8f9e0d1c2b3a4f5"
        result = format_hash(full_hash)
        
        # Should be truncated with ellipsis
        assert result.endswith("...")
        assert len(result) < len(full_hash)
    
    def test_format_difficulty(self):
        """Test difficulty formatting."""
        result = format_difficulty(84.2e12)
        
        assert "T" in result
        assert "84" in result


# Simple test runner (for systems without pytest)
def run_tests():
    """Run all tests manually."""
    test_classes = [TestAPICache, TestBitcoinAPIMock, TestFormatting]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 60)
        
        test_instance = test_class()
        
        # Get all test methods
        test_methods = [method for method in dir(test_instance) 
                       if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                print(f"  ✓ {method_name}")
                passed_tests += 1
            except AssertionError as e:
                print(f"  ✗ {method_name}: {e}")
                failed_tests += 1
            except Exception as e:
                print(f"  ✗ {method_name}: {type(e).__name__}: {e}")
                failed_tests += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests: {total_tests} total, {passed_tests} passed, {failed_tests} failed")
    
    return failed_tests == 0


if __name__ == '__main__':
    # Try to use pytest if available
    try:
        import pytest
        pytest.main([__file__, '-v'])
    except ImportError:
        # Fall back to manual test runner
        print("pytest not found, running manual tests...")
        success = run_tests()
        sys.exit(0 if success else 1)
