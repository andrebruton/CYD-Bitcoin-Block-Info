"""Main application controller for Bitcoin information display."""

import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime


class AppController:
    """Main application controller managing WiFi, Bitcoin data, and display."""
    
    def __init__(self, display_manager=None,
                 wifi_manager=None,
                 bitcoin_fetcher=None):
        """
        Initialize application controller.
        
        Args:
            display_manager: Display manager instance
            wifi_manager: WiFi manager instance
            bitcoin_fetcher: Bitcoin fetcher instance
        """
        # Lazy imports to avoid circular dependencies
        if display_manager is None:
            from src.display.manager import DisplayManager
            display_manager = DisplayManager(mock=True)
        
        if bitcoin_fetcher is None:
            from src.bitcoin.fetcher import BitcoinFetcher
            bitcoin_fetcher = BitcoinFetcher(mock=True)
        
        self.display = display_manager
        self.wifi = wifi_manager
        self.bitcoin = bitcoin_fetcher
        
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        self.update_interval = 30  # Update every 30 seconds
        self.wifi_check_interval = 60  # Check WiFi every 60 seconds
        self.last_wifi_check = 0
        self.is_wifi_connected = False
        self.bitcoin_data: Dict[str, Any] = {}
        
    def start(self):
        """Start the application."""
        self.running = True
        self.display.show_loading("Initializing...")
        
        # Check if WiFi credentials exist
        if self.wifi and self.wifi.load_config():
            self._connect_wifi()
        else:
            self._show_wifi_setup()
        
        # Start update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
    
    def stop(self):
        """Stop the application."""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
    
    def _connect_wifi(self):
        """Attempt to connect to saved WiFi."""
        self.display.show_connecting_wifi()
        
        connected = self.wifi.connect()
        self.is_wifi_connected = connected
        
        if connected:
            print(f"[APP] Connected to WiFi: {self.wifi.current_ssid}")
            self._fetch_bitcoin_data()
        else:
            print("[APP] WiFi connection failed")
            self._show_wifi_setup()
    
    def _show_wifi_setup(self):
        """Show WiFi setup screen."""
        self.display.show_ap_mode()
        self.is_wifi_connected = False
        
        # Start AP mode and web server
        print("[APP] Starting WiFi setup in AP mode")
        if self.wifi:
            self.wifi.setup_ap()
    
    def _fetch_bitcoin_data(self):
        """Fetch Bitcoin data from APIs."""
        self.display.show_loading("Fetching Bitcoin data...")
        
        try:
            price = self.bitcoin.fetch_price()
            block = self.bitcoin.fetch_latest_block()
            difficulty = self.bitcoin.fetch_difficulty()
            
            # Store data as dictionaries for display
            self.bitcoin_data = {
                'price': price.to_dict() if price else None,
                'block': block.to_dict() if block else None,
                'difficulty': difficulty.to_dict() if difficulty else None
            }
            
            if block and block.time:
                self.display.set_last_block_time(block.time)
            
            self._show_bitcoin_info()
            
        except Exception as e:
            print(f"[APP] Error fetching Bitcoin data: {e}")
            self.display.show_error("API Error", str(e))
    
    def _show_bitcoin_info(self):
        """Display Bitcoin information."""
        local_time = datetime.now().strftime("%H:%M:%S")
        
        self.display.show_bitcoin_info(
            price=self.bitcoin_data.get('price'),
            block=self.bitcoin_data.get('block'),
            difficulty=self.bitcoin_data.get('difficulty'),
            local_time=local_time
        )
    
    def _update_loop(self):
        """Main update loop running in background thread."""
        while self.running:
            try:
                # Check WiFi status periodically
                if time.time() - self.last_wifi_check > self.wifi_check_interval:
                    self._check_wifi_status()
                    self.last_wifi_check = time.time()
                
                # Update Bitcoin data if connected
                if self.is_wifi_connected:
                    if time.time() - self.display.last_update > self.update_interval:
                        self._fetch_bitcoin_data()
                    else:
                        # Update time display
                        self._show_bitcoin_info()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"[APP] Error in update loop: {e}")
                time.sleep(10)
    
    def _check_wifi_status(self):
        """Check if WiFi is still connected."""
        # In real implementation, would check actual WiFi status
        # For now, assume connected if we don't have an error
        if not self.is_wifi_connected:
            self.display.show_offline("No WiFi Connection")
    
    def on_button_press(self, button_id: str):
        """
        Handle button press event.
        
        Args:
            button_id: Identifier of pressed button
        """
        if button_id == "reset":
            self._reset_wifi()
    
    def _reset_wifi(self):
        """Reset WiFi configuration."""
        print("[APP] Resetting WiFi configuration")
        if self.wifi:
            self.wifi.reset()
        self.is_wifi_connected = False
        self._show_wifi_setup()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current application status."""
        return {
            'running': self.running,
            'display_state': self.display.current_state,
            'wifi_connected': self.is_wifi_connected,
            'wifi_ssid': self.wifi.current_ssid if self.wifi else 'N/A',
            'bitcoin_data': self.bitcoin_data,
            'last_update': self.display.last_update
        }

