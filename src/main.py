"""
Main Orchestrator

Coordinates data fetching, display updates, and timing.
This is the entry point for the CYD Bitcoin application.

On ESP32, starts a WiFi setup portal if credentials are not available.

Usage:
    python main.py                    # Run with mock data (PC testing)
    python main.py --real             # Run with real APIs
    python main.py --mock --debug     # Run with debugging
"""

import time
import sys
from bitcoin_api import BitcoinAPI
from display_manager import DisplayManager


class BitcoinApp:
    """Main application controller."""
    
    def __init__(self, use_real_api=True, mock_display=True, debug=False, skip_wifi_check=False):
        """
        Initialize the Bitcoin app.
        
        Args:
            use_real_api: Use real APIs (False = mock data)
            mock_display: Use mock display (False = real display)
            debug: Enable debug output
            skip_wifi_check: Skip WiFi connection check (for testing)
        """
        self.use_real_api = use_real_api
        self.mock_display = mock_display
        self.debug = debug
        
        # Check WiFi connection (skip for PC testing)
        if not skip_wifi_check and not mock_display:
            self._check_wifi_connected()
        
        # Initialize components
        self.api = BitcoinAPI(use_mock_data=not use_real_api, timeout=5)
        self.display = DisplayManager(mock_mode=mock_display, debug=debug)
        
        # State tracking
        self.last_price = None
        self.last_block_height = None
        self.running = True
        
        # Timing
        self.refresh_intervals = {
            'price': 60,          # Update price every 60s
            'block': 10,          # Check for new blocks every 10s
            'display': 1,         # Update display every 1s
        }
        self.last_update = {
            'price': 0,
            'block': 0,
            'display': 0,
        }
        
        if self.debug:
            print("BitcoinApp initialized")
            print(f"  Real API: {use_real_api}")
            print(f"  Mock Display: {mock_display}")
    
    def _check_wifi_connected(self):
        """
        Check if WiFi is connected.
        
        Raises:
            RuntimeError if WiFi is not connected
        """
        try:
            from wifi_manager import WiFiManager
            wifi = WiFiManager(debug=self.debug)
            
            if not wifi.is_connected():
                raise RuntimeError("WiFi not connected. Run boot.py first.")
            
            if self.debug:
                ip = wifi.get_ip_address()
                print(f"WiFi check passed. IP: {ip}")
        
        except ImportError:
            # WiFi module not available (PC mode), skip check
            pass
    
    def run(self, duration=None):
        """
        Run the main application loop.
        
        Args:
            duration: Run for N seconds (None = run forever)
        """
        print("Bitcoin Display App Starting...")
        print("Press Ctrl+C to exit\n")
        
        start_time = time.time()
        
        try:
            while self.running:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Check if we should stop
                if duration and elapsed > duration:
                    break
                
                # Update the display before potentially slow network requests.
                if current_time - self.last_update['display'] >= self.refresh_intervals['display']:
                    self._render_display()
                    self.last_update['display'] = time.time()

                # Update price
                if current_time - self.last_update['price'] > self.refresh_intervals['price']:
                    self._update_price()
                    self.last_update['price'] = time.time()
                
                # Check for new block
                if current_time - self.last_update['block'] > self.refresh_intervals['block']:
                    self._update_block()
                    self.last_update['block'] = time.time()
                
                # Sleep briefly to avoid busy-waiting
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n\nShutdown requested by user")
        except Exception as e:
            print(f"\nError in main loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()
    
    def _update_price(self):
        """Fetch and update Bitcoin price."""
        if self.debug:
            print("[PRICE] Fetching...")
        
        try:
            if self.last_price is None:
                self.display.show_loading("Fetching price...")
            price = self.api.get_price()
            
            if price:
                self.last_price = price
                if self.debug:
                    print(f"[PRICE] Updated: ${price['usd']:.2f}")
            else:
                if self.debug:
                    print("[PRICE] Failed to fetch, using last known")
        
        except Exception as e:
            print(f"[PRICE] Error: {e}")
            self.api.price_fresh = False
            self.display.show_error(f"Price fetch failed")
    
    def _update_block(self):
        """Fetch and update block information."""
        if self.debug:
            print("[BLOCK] Fetching...")
        
        try:
            block = self.api.get_block()
            if self.api.use_mock_data:
                self.api.get_difficulty()
            
            if block:
                current_height = block.get('height')
                
                # Check if new block found
                if self.last_block_height and current_height > self.last_block_height:
                    print(f"\n🎉 NEW BLOCK FOUND: #{current_height}")
                
                self.last_block_height = current_height
                
                if self.debug:
                    print(f"[BLOCK] Block #{current_height} at {block.get('time')}")
            else:
                if self.debug:
                    print("[BLOCK] Failed to fetch")
        
        except Exception as e:
            print(f"[BLOCK] Error: {e}")
            self.api.block_fresh = False
    
    def _render_display(self):
        """Render current state to display."""
        try:
            wifi_connected = None
            if sys.platform == 'esp32':
                import network
                wifi_connected = network.WLAN(network.STA_IF).isconnected()
            data = {
                'price': self.last_price,
                'block': self.api.last_block,
                'difficulty': self.api.last_difficulty,
                'wifi_connected': wifi_connected,
                'price_updated_at': self.api.price_updated_at,
                'block_updated_at': self.api.block_updated_at,
                'price_fresh': self.api.price_fresh,
                'block_fresh': self.api.block_fresh,
            }
            
            self.display.render_full_screen(data)
        
        except Exception as e:
            print(f"[DISPLAY] Error: {e}")
            self.display.show_error("Display error")
    
    def shutdown(self):
        """Clean shutdown."""
        print("\nShutting down...")
        self.running = False
        self.display.clear_screen()
        print("Goodbye!")


def setup_wifi(display):
    """Connect to saved WiFi or start a temporary configuration portal."""
    import binascii
    import os
    from wifi_manager import WiFiManager

    wifi = WiFiManager()

    def connect(credentials):
        display.show_loading("Connecting to WiFi...")
        for status in wifi.connect_to_wifi(
            credentials['ssid'], credentials['password'], timeout=30
        ):
            if status['status'] == 'connected':
                print("[WiFi] Connected")
                return True
            if status['status'] == 'failed':
                print(f"[WiFi] {status['error']}")
        return False

    credentials = wifi.load_credentials()
    if credentials and connect(credentials):
        return

    from wifi_web_server import WiFiWebServer

    while True:
        password = binascii.hexlify(os.urandom(6)).decode('ascii')
        if not wifi.start_ap_mode("CYDBitcoin", password):
            raise RuntimeError("Could not start WiFi setup access point")
        server = WiFiWebServer(wifi, debug=True)
        if not server.start():
            wifi.stop_ap_mode()
            raise RuntimeError("Could not start WiFi setup server")
        display.show_setup_portal("CYDBitcoin", password, wifi.get_ap_ip_address())
        print("[WiFi] Setup portal ready; see the display for connection details")
        try:
            while True:
                result = server.handle_request()
                if result and result.get('saved'):
                    break
        finally:
            server.stop()
            wifi.stop_ap_mode()

        credentials = wifi.load_credentials()
        if credentials and connect(credentials):
            return
        print("[WiFi] Connection failed; reopening setup portal")


def main():
    """Entry point for the application."""
    # Parse command line arguments
    use_real_api = '--real' in sys.argv or (
        sys.platform == 'esp32' and '--mock' not in sys.argv
    )
    mock_display = sys.platform != 'esp32' or '--mock' in sys.argv
    debug = '--debug' in sys.argv
    
    # Adjust display mode if requested
    if '--display' in sys.argv:
        mock_display = False
    
    # Create and run app
    app = BitcoinApp(
        use_real_api=use_real_api,
        mock_display=mock_display,
        debug=debug,
        skip_wifi_check=sys.platform == 'esp32'
    )

    if sys.platform == 'esp32' and not mock_display:
        try:
            setup_wifi(app.display)
            app._render_display()
        except (OSError, ValueError, RuntimeError) as e:
            print(f"[WiFi] Setup failed: {e}")
            app.display.show_error("WiFi setup failed")
            return
        try:
            import ntptime
            ntptime.settime()
        except (ImportError, OSError) as e:
            print(f"[Time] Clock synchronization failed: {e}")
    
    # Run for limited time in testing, or forever in production
    duration = 30 if '--test' in sys.argv else None
    
    app.run(duration=duration)


if __name__ == '__main__':
    main()
