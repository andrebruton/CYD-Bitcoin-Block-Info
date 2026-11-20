"""
WiFi Manager

Handles WiFi connectivity, credential persistence, and AP mode.
Supports both ESP32 (MicroPython) and PC (mock mode for testing).
"""

import json
import time
import os


class WiFiManager:
    """
    Manages WiFi connections and configuration.
    
    Features:
    - Load/save credentials to flash (JSON file)
    - Connect to saved WiFi with timeout and retry
    - Start AP (Access Point) mode for setup
    - Get signal strength and connection status
    - Fallback to mock mode for PC testing
    """
    
    def __init__(self, credentials_file="/wifi_credentials.json", debug=False):
        """
        Initialize WiFi manager.
        
        Args:
            credentials_file: Path to JSON file for storing credentials
            debug: Print debug information
        """
        self.credentials_file = credentials_file
        self.debug = debug
        self.wlan = None
        self.ap = None
        self.ssid = None
        self.password = None
        self.is_mock = False
        
        # Try to import network (ESP32 MicroPython)
        try:
            import network
            self.network = network
        except ImportError:
            # Mock mode for PC testing
            self.network = None
            self.is_mock = True
            if debug:
                print("[WiFi] Mock mode (no network module)")
    
    def load_credentials(self):
        """
        Load WiFi credentials from flash.
        
        Returns:
            Dict with 'ssid' and 'password', or None if not found
        """
        try:
            with open(self.credentials_file, 'r') as f:
                data = json.load(f)
                self.ssid = data.get('ssid')
                self.password = data.get('password')
                
                if self.debug:
                    print(f"[WiFi] Credentials loaded: SSID={self.ssid}")
                
                return {'ssid': self.ssid, 'password': self.password}
        
        except OSError as e:
            if e.args and e.args[0] == 2:
                return None
            print(f"[WiFi] Error loading credentials: {e}")
            raise
        except ValueError as e:
            print(f"[WiFi] Invalid credentials file: {e}")
            raise
    
    def save_credentials(self, ssid, password):
        """
        Save WiFi credentials to flash.
        
        Args:
            ssid: WiFi network name
            password: WiFi password
        
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {'ssid': ssid, 'password': password}
            
            with open(self.credentials_file, 'w') as f:
                json.dump(data, f)
            
            self.ssid = ssid
            self.password = password
            
            if self.debug:
                print(f"[WiFi] Credentials saved: SSID={ssid}")
            
            return True
        
        except OSError as e:
            print(f"[WiFi] Error saving credentials: {e}")
            return False
    
    def clear_credentials(self):
        """Clear saved WiFi credentials."""
        try:
            os.remove(self.credentials_file)
        except OSError as e:
            if not e.args or e.args[0] != 2:
                print(f"[WiFi] Error clearing credentials: {e}")
                return False
        self.ssid = None
        self.password = None
        if self.debug:
            print("[WiFi] Credentials cleared")
        return True
    
    def start_ap_mode(self, ap_name="CYDBitcoin", ap_password="12345678"):
        """
        Start WiFi Access Point (AP) mode for setup.
        
        Args:
            ap_name: Name of the AP (SSID)
            ap_password: Password for AP (must be 8+ chars)
        
        Returns:
            True if successful, False otherwise
        """
        if self.is_mock:
            if self.debug:
                print(f"[WiFi-Mock] AP Mode: {ap_name}")
            return True
        
        try:
            # Turn off station mode if it was on
            self.wlan = self.network.WLAN(self.network.STA_IF)
            self.wlan.active(False)
            
            # Start AP mode
            self.ap = self.network.WLAN(self.network.AP_IF)
            self.ap.active(True)
            self.ap.config(
                essid=ap_name,
                password=ap_password,
                authmode=self.network.AUTH_WPA2_PSK,
            )
            
            if self.debug:
                print(f"[WiFi] AP Mode started: {ap_name}")
                print(f"[WiFi] AP IP: {self.ap.ifconfig()[0]}")
            
            return True
        
        except Exception as e:
            if self.debug:
                print(f"[WiFi] Error starting AP mode: {e}")
            return False
    
    def stop_ap_mode(self):
        """Stop WiFi Access Point mode."""
        if self.is_mock:
            return True
        
        try:
            if self.ap:
                self.ap.active(False)
            if self.debug:
                print("[WiFi] AP Mode stopped")
            return True
        except Exception as e:
            if self.debug:
                print(f"[WiFi] Error stopping AP mode: {e}")
            return False
    
    def connect_to_wifi(self, ssid, password, timeout=300, retry_interval=10):
        """
        Connect to WiFi network with timeout and retry.
        
        Args:
            ssid: WiFi network name
            password: WiFi password
            timeout: Max time to try connecting (seconds)
            retry_interval: Time between retry attempts (seconds)
        
        Yields:
            Dict with status updates:
            {
                'status': 'connecting'|'connected'|'failed',
                'attempt': current attempt number,
                'total_attempts': total attempts,
                'signal_strength': signal % (or None),
                'time_remaining': seconds left,
                'error': error message (if failed)
            }
        """
        if self.is_mock:
            # Mock mode: instant success
            yield {
                'status': 'connected',
                'attempt': 1,
                'total_attempts': 1,
                'signal_strength': 85,
                'time_remaining': 0,
                'error': None
            }
            return
        
        try:
            self.wlan = self.network.WLAN(self.network.STA_IF)
            self.wlan.active(True)
            
            # Stop AP mode if running
            if self.ap:
                self.ap.active(False)
            
            start_time = time.time()
            attempt = 0
            total_attempts = timeout // retry_interval
            
            while time.time() - start_time < timeout:
                attempt += 1
                
                # Try to connect
                if not self.wlan.isconnected():
                    self.wlan.connect(ssid, password)
                
                # Check if connected
                for _ in range(retry_interval):
                    if self.wlan.isconnected():
                        signal = self.get_signal_strength()
                        yield {
                            'status': 'connected',
                            'attempt': attempt,
                            'total_attempts': total_attempts,
                            'signal_strength': signal,
                            'time_remaining': 0,
                            'error': None
                        }
                        self.ssid = ssid
                        self.password = password
                        return
                    
                    time.sleep(1)
                
                # Still not connected, yield progress
                elapsed = time.time() - start_time
                remaining = timeout - elapsed
                signal = self.get_signal_strength()
                
                yield {
                    'status': 'connecting',
                    'attempt': attempt,
                    'total_attempts': total_attempts,
                    'signal_strength': signal,
                    'time_remaining': int(remaining),
                    'error': None
                }
            
            # Timeout reached
            yield {
                'status': 'failed',
                'attempt': attempt,
                'total_attempts': total_attempts,
                'signal_strength': self.get_signal_strength(),
                'time_remaining': 0,
                'error': 'Connection timeout (5 minutes)'
            }
        
        except Exception as e:
            yield {
                'status': 'failed',
                'attempt': 0,
                'total_attempts': 0,
                'signal_strength': None,
                'time_remaining': 0,
                'error': f"Connection error: {str(e)}"
            }
    
    def is_connected(self):
        """
        Check if currently connected to WiFi.
        
        Returns:
            True if connected, False otherwise
        """
        if self.is_mock:
            return True
        
        try:
            if self.wlan is None:
                self.wlan = self.network.WLAN(self.network.STA_IF)
            if self.wlan and self.wlan.isconnected():
                return True
        except OSError as e:
            print(f"[WiFi] Error checking connection: {e}")
        
        return False
    
    def disconnect(self):
        """Disconnect from WiFi."""
        if self.is_mock:
            return True
        
        try:
            if self.wlan:
                self.wlan.active(False)
            if self.debug:
                print("[WiFi] Disconnected")
            return True
        except Exception as e:
            if self.debug:
                print(f"[WiFi] Error disconnecting: {e}")
            return False
    
    def get_signal_strength(self):
        """
        Get WiFi signal strength as percentage.
        
        Returns:
            Signal strength 0-100 (or None if not connected)
        """
        if self.is_mock:
            return 75
        
        try:
            if self.wlan and self.wlan.isconnected():
                # RSSI (Received Signal Strength Indicator) is negative
                # Typical range: -30 (excellent) to -90 (poor)
                rssi = self.wlan.status('rssi')
                # Convert to 0-100 scale
                # -30 dbm = 100%, -90 dbm = 0%
                signal = max(0, min(100, (rssi + 90) * 100 // 60))
                return signal
        except Exception:
            pass
        
        return None
    
    def get_ip_address(self):
        """
        Get current IP address.
        
        Returns:
            IP address string, or None if not connected
        """
        if self.is_mock:
            return "192.168.1.100"
        
        try:
            if self.wlan and self.wlan.isconnected():
                config = self.wlan.ifconfig()
                return config[0]
        except Exception:
            pass
        
        return None
    
    def get_ap_ip_address(self):
        """
        Get AP mode IP address (192.168.4.1).
        
        Returns:
            IP address string
        """
        if self.is_mock:
            return "192.168.4.1"
        
        try:
            if self.ap:
                config = self.ap.ifconfig()
                return config[0]
        except Exception:
            pass
        
        return "192.168.4.1"


# For testing
if __name__ == '__main__':
    wm = WiFiManager(debug=True)
    
    # Test 1: Load credentials (should return None on first run)
    creds = wm.load_credentials()
    print(f"Test 1 - Load: {creds}")
    
    # Test 2: Save credentials
    result = wm.save_credentials("TestNetwork", "password123")
    print(f"Test 2 - Save: {result}")
    
    # Test 3: Load again (should return saved creds)
    creds = wm.load_credentials()
    print(f"Test 3 - Load again: {creds}")
    
    # Test 4: AP mode
    result = wm.start_ap_mode("CYDBitcoin", "12345678")
    print(f"Test 4 - AP Mode: {result}")
    
    # Test 5: Mock connection
    print("Test 5 - Connecting (mock mode):")
    for status in wm.connect_to_wifi("TestNetwork", "password123", timeout=10):
        print(f"  {status}")
    
    # Test 6: Check connection
    connected = wm.is_connected()
    print(f"Test 6 - Connected: {connected}")
    
    # Test 7: Get IP
    ip = wm.get_ip_address()
    print(f"Test 7 - IP: {ip}")
    
    # Test 8: Clear credentials
    result = wm.clear_credentials()
    print(f"Test 8 - Clear: {result}")
