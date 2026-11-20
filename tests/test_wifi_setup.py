"""
Tests for WiFi Setup

Unit tests for WiFi manager and web server components.
Run with: pytest tests/test_wifi_setup.py -v
"""

import pytest
import json
import os
import tempfile
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from wifi_manager import WiFiManager
from wifi_web_server import WiFiWebServer


class TestWiFiManager:
    """Tests for WiFiManager class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def wifi_manager(self, temp_dir):
        """Create WiFiManager with temp credentials file."""
        cred_file = os.path.join(temp_dir, 'wifi_creds.json')
        return WiFiManager(credentials_file=cred_file, debug=False)
    
    def test_load_credentials_not_found(self, wifi_manager):
        """Test loading credentials when file doesn't exist."""
        result = wifi_manager.load_credentials()
        assert result is None
    
    def test_save_credentials(self, wifi_manager):
        """Test saving credentials to file."""
        result = wifi_manager.save_credentials("TestSSID", "TestPassword123")
        assert result is True
        assert wifi_manager.ssid == "TestSSID"
        assert wifi_manager.password == "TestPassword123"
    
    def test_save_and_load_credentials(self, wifi_manager):
        """Test save and load cycle."""
        # Save
        wifi_manager.save_credentials("MyNetwork", "password123")
        
        # Create new manager pointing to same file
        wifi_manager2 = WiFiManager(
            credentials_file=wifi_manager.credentials_file,
            debug=False
        )
        
        # Load
        result = wifi_manager2.load_credentials()
        assert result is not None
        assert result['ssid'] == "MyNetwork"
        assert result['password'] == "password123"
    
    def test_clear_credentials(self, wifi_manager):
        """Test clearing credentials."""
        # Save first
        wifi_manager.save_credentials("TestSSID", "TestPassword")
        assert wifi_manager.ssid is not None
        
        # Clear
        result = wifi_manager.clear_credentials()
        assert result is True
        assert wifi_manager.ssid is None
        
        # Verify cleared
        result = wifi_manager.load_credentials()
        assert result is None
    
    def test_start_ap_mode_mock(self, wifi_manager):
        """Test AP mode startup in mock mode."""
        # Mock mode should always succeed
        result = wifi_manager.start_ap_mode("TestAP", "password123")
        assert result is True
    
    def test_stop_ap_mode_mock(self, wifi_manager):
        """Test AP mode stop in mock mode."""
        result = wifi_manager.stop_ap_mode()
        assert result is True
    
    def test_connect_to_wifi_mock(self, wifi_manager):
        """Test WiFi connection in mock mode."""
        statuses = []
        for status in wifi_manager.connect_to_wifi("TestSSID", "password123", timeout=10):
            statuses.append(status)
        
        # Should have at least one status
        assert len(statuses) > 0
        
        # Last status should be connected
        last_status = statuses[-1]
        assert last_status['status'] == 'connected'
        assert last_status['signal_strength'] is not None
    
    def test_is_connected_mock(self, wifi_manager):
        """Test connection status check in mock mode."""
        is_connected = wifi_manager.is_connected()
        assert is_connected is True
    
    def test_get_signal_strength_mock(self, wifi_manager):
        """Test signal strength reporting in mock mode."""
        signal = wifi_manager.get_signal_strength()
        assert signal is not None
        assert 0 <= signal <= 100
    
    def test_get_ip_address_mock(self, wifi_manager):
        """Test IP address retrieval in mock mode."""
        ip = wifi_manager.get_ip_address()
        assert ip is not None
        assert isinstance(ip, str)
    
    def test_get_ap_ip_address_mock(self, wifi_manager):
        """Test AP IP address retrieval in mock mode."""
        ip = wifi_manager.get_ap_ip_address()
        assert ip is not None
        assert ip == "192.168.4.1"
    
    def test_credentials_file_corruption(self, temp_dir):
        """Test handling of corrupted credentials file."""
        cred_file = os.path.join(temp_dir, 'corrupted.json')
        
        # Write corrupted JSON
        with open(cred_file, 'w') as f:
            f.write("{invalid json")
        
        wm = WiFiManager(credentials_file=cred_file, debug=False)
        with pytest.raises(ValueError):
            wm.load_credentials()
    
    def test_special_characters_in_password(self, wifi_manager):
        """Test handling special characters in password."""
        special_pass = "P@ssw0rd!#$%&*()_+-=[]{}|;':\",./<>?"
        
        wifi_manager.save_credentials("TestSSID", special_pass)
        
        # Create new manager and load
        wm2 = WiFiManager(
            credentials_file=wifi_manager.credentials_file,
            debug=False
        )
        result = wm2.load_credentials()
        
        assert result is not None
        assert result['password'] == special_pass


class TestWiFiWebServer:
    """Tests for WiFiWebServer class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def mock_wifi_manager(self, temp_dir):
        """Create mock WiFi manager for testing."""
        wm = WiFiManager(
            credentials_file=os.path.join(temp_dir, 'creds.json'),
            debug=False
        )
        return wm
    
    @pytest.fixture
    def web_server(self, mock_wifi_manager):
        """Create web server instance."""
        return WiFiWebServer(mock_wifi_manager, debug=False)
    
    def test_web_server_init(self, web_server):
        """Test web server initialization."""
        assert web_server is not None
        assert web_server.running is False
    
    def test_get_html_form(self, web_server):
        """Test HTML form generation."""
        html = web_server._get_html_form()
        
        # Check form structure
        assert isinstance(html, str)
        assert len(html) > 0
        assert '<form' in html
        assert '<input' in html
        assert 'ssid' in html
        assert 'password' in html
        assert 'submit' in html.lower()
    
    def test_html_form_size(self, web_server):
        """Test HTML form is reasonably small (memory efficient)."""
        html = web_server._get_html_form()
        
        # Should be less than 10KB for memory efficiency
        assert len(html) < 10 * 1024
    
    def test_web_server_start_mock(self, web_server):
        """Test web server start (will be in mock mode without socket)."""
        result = web_server.start()
        # Should attempt to start (may fail on PC if port in use, that's ok)
        # What matters is it doesn't crash
        assert isinstance(result, bool)
    
    def test_web_server_stop(self, web_server):
        """Test web server stop."""
        web_server.start()
        result = web_server.stop()
        
        # Should complete without error
        assert web_server.running is False

    def test_fragmented_form_decodes_special_characters(self, web_server, mock_wifi_manager):
        body = b'ssid=My+WiFi&password=P%40ss%26word%2B%25'
        request = (
            b'POST /save HTTP/1.1\r\nContent-Length: '
            + str(len(body)).encode() + b'\r\n\r\n' + body
        )

        class Client:
            def __init__(self):
                self.chunks = [request[:35], request[35:60], request[60:]]
                self.response = b''

            def settimeout(self, timeout):
                pass

            def recv(self, size):
                return self.chunks.pop(0)

            def sendall(self, data):
                self.response += data

            def close(self):
                pass

        client = Client()

        class Server:
            def accept(self):
                return client, None

        web_server.server = Server()
        web_server.running = True
        result = web_server.handle_request()
        assert result['saved'] is True
        assert mock_wifi_manager.load_credentials() == {
            'ssid': 'My WiFi', 'password': 'P@ss&word+%'
        }
        assert b'200 OK' in client.response

    def test_save_failure_is_not_reported_as_success(self, web_server, monkeypatch):
        body = b'ssid=test&password=secret'
        request = (
            b'POST /save HTTP/1.1\r\nContent-Length: '
            + str(len(body)).encode() + b'\r\n\r\n' + body
        )

        class Client:
            def settimeout(self, timeout):
                pass

            def recv(self, size):
                return request

            def sendall(self, data):
                self.response = data

            def close(self):
                pass

        client = Client()

        class Server:
            def accept(self):
                return client, None

        monkeypatch.setattr(web_server.wifi_manager, 'save_credentials', lambda *args: False)
        web_server.server = Server()
        web_server.running = True
        assert web_server.handle_request()['error'] == 'Could not save credentials'
        assert b'500 Internal Server Error' in client.response


class TestWiFiIntegration:
    """Integration tests for WiFi setup flow."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_full_setup_flow(self, temp_dir):
        """Test complete WiFi setup and connection flow."""
        
        # Step 1: Check no credentials exist
        wm = WiFiManager(
            credentials_file=os.path.join(temp_dir, 'creds.json'),
            debug=False
        )
        creds = wm.load_credentials()
        assert creds is None
        
        # Step 2: Simulate user entering credentials via web form
        ws = WiFiWebServer(wm, debug=False)
        ws.wifi_manager.save_credentials("MyHomeWiFi", "password123")
        
        # Step 3: Verify credentials were saved
        wm2 = WiFiManager(
            credentials_file=os.path.join(temp_dir, 'creds.json'),
            debug=False
        )
        creds = wm2.load_credentials()
        assert creds is not None
        assert creds['ssid'] == "MyHomeWiFi"
        
        # Step 4: Try to connect (mock will succeed immediately)
        statuses = []
        for status in wm2.connect_to_wifi("MyHomeWiFi", "password123", timeout=10):
            statuses.append(status)
        
        # Should have at least one status
        assert len(statuses) > 0
        
        # Should be connected
        last_status = statuses[-1]
        assert last_status['status'] == 'connected'
    
    def test_reset_wifi_flow(self, temp_dir):
        """Test WiFi reset flow."""
        
        # Save initial credentials
        wm = WiFiManager(
            credentials_file=os.path.join(temp_dir, 'creds.json'),
            debug=False
        )
        wm.save_credentials("OldNetwork", "oldpassword")
        
        # Verify saved
        creds = wm.load_credentials()
        assert creds is not None
        
        # Clear/reset
        wm.clear_credentials()
        
        # Verify cleared
        creds = wm.load_credentials()
        assert creds is None
    
    def test_concurrent_managers(self, temp_dir):
        """Test multiple managers accessing same credentials file."""
        cred_file = os.path.join(temp_dir, 'shared_creds.json')
        
        # Manager 1: Save credentials
        wm1 = WiFiManager(credentials_file=cred_file, debug=False)
        wm1.save_credentials("SharedNetwork", "sharedpass123")
        
        # Manager 2: Load same credentials
        wm2 = WiFiManager(credentials_file=cred_file, debug=False)
        creds = wm2.load_credentials()
        
        # Should be the same
        assert creds is not None
        assert creds['ssid'] == "SharedNetwork"
        assert creds['password'] == "sharedpass123"


class TestWiFiEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_empty_ssid(self, temp_dir):
        """Test handling of empty SSID."""
        wm = WiFiManager(
            credentials_file=os.path.join(temp_dir, 'creds.json'),
            debug=False
        )
        
        # Try to save empty SSID (should still work)
        result = wm.save_credentials("", "password")
        assert result is True
    
    def test_very_long_ssid(self, temp_dir):
        """Test handling of very long SSID."""
        wm = WiFiManager(
            credentials_file=os.path.join(temp_dir, 'creds.json'),
            debug=False
        )
        
        # WiFi SSID can be up to 32 characters
        long_ssid = "A" * 32
        result = wm.save_credentials(long_ssid, "password")
        assert result is True
        
        # Verify it was saved correctly
        creds = wm.load_credentials()
        assert creds['ssid'] == long_ssid
    
    def test_unicode_in_credentials(self, temp_dir):
        """Test handling of Unicode characters in credentials."""
        wm = WiFiManager(
            credentials_file=os.path.join(temp_dir, 'creds.json'),
            debug=False
        )
        
        # Try Unicode SSID (should work with JSON)
        result = wm.save_credentials("WiFi_🏠", "password123")
        assert result is True
        
        # Verify saved
        creds = wm.load_credentials()
        assert creds['ssid'] == "WiFi_🏠"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
