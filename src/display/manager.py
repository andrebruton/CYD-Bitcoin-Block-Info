"""Display manager for CYD (Cheap Yellow Display) ESP32 board."""

import time
from typing import Optional, Dict, Any, Tuple, Callable
from abc import ABC, abstractmethod


class DisplayBase(ABC):
    """Abstract base class for display implementations."""
    
    def __init__(self, width: int = 320, height: int = 240):
        """Initialize display with dimensions."""
        self.width = width
        self.height = height
        
    @abstractmethod
    def clear(self):
        """Clear the display."""
        pass
    
    @abstractmethod
    def fill(self, color: Tuple[int, int, int]):
        """Fill display with color (R, G, B)."""
        pass
    
    @abstractmethod
    def text(self, text: str, x: int, y: int, color: Tuple[int, int, int], 
             size: int = 1, centered: bool = False):
        """Draw text on display."""
        pass
    
    @abstractmethod
    def show(self):
        """Update/show display."""
        pass


class MockDisplay(DisplayBase):
    """Mock display for testing (outputs to console)."""
    
    def __init__(self, width: int = 320, height: int = 240):
        super().__init__(width, height)
        self.buffer = []
        self._print_operations = True
        
    def clear(self):
        """Clear display buffer."""
        self.buffer = []
        if self._print_operations:
            print(f"[DISPLAY] Cleared ({self.width}x{self.height})")
    
    def fill(self, color: Tuple[int, int, int]):
        """Fill with color."""
        if self._print_operations:
            r, g, b = color
            print(f"[DISPLAY] Fill RGB({r}, {g}, {b})")
    
    def text(self, text: str, x: int, y: int, color: Tuple[int, int, int],
             size: int = 1, centered: bool = False):
        """Draw text."""
        self.buffer.append({
            'type': 'text',
            'text': text,
            'x': x,
            'y': y,
            'color': color,
            'size': size,
            'centered': centered
        })
        if self._print_operations:
            print(f"[DISPLAY] Text at ({x},{y}): {text}")
    
    def show(self):
        """Display all buffered operations."""
        if self._print_operations and self.buffer:
            print("[DISPLAY] ===== SHOW =====")
            for op in self.buffer:
                if op['type'] == 'text':
                    print(f"  {op['text']}")


class SPIDisplay(DisplayBase):
    """Real SPI display for CYD hardware."""
    
    def __init__(self, width: int = 320, height: int = 240):
        super().__init__(width, height)
        self.spi = None
        self.cs_pin = None
        self.dc_pin = None
        self.rst_pin = None
        
    def initialize(self, spi, cs_pin, dc_pin, rst_pin):
        """Initialize with actual hardware pins."""
        self.spi = spi
        self.cs_pin = cs_pin
        self.dc_pin = dc_pin
        self.rst_pin = rst_pin
        
    def clear(self):
        """Clear the display."""
        if not self.spi:
            return
        self.fill((0, 0, 0))
    
    def fill(self, color: Tuple[int, int, int]):
        """Fill display with color."""
        if not self.spi:
            return
        # Actual SPI implementation would go here
        pass
    
    def text(self, text: str, x: int, y: int, color: Tuple[int, int, int],
             size: int = 1, centered: bool = False):
        """Draw text using font rendering."""
        if not self.spi:
            return
        # Font rendering would go here
        pass
    
    def show(self):
        """Update display (buffer flush)."""
        if not self.spi:
            return


class DisplayManager:
    """Manages display of Bitcoin information with state and updates."""
    
    # Colors (RGB tuples)
    COLOR_BLACK = (0, 0, 0)
    COLOR_WHITE = (255, 255, 255)
    COLOR_BLUE = (0, 100, 255)
    COLOR_GREEN = (0, 200, 0)
    COLOR_RED = (255, 0, 0)
    COLOR_YELLOW = (255, 200, 0)
    COLOR_GRAY = (100, 100, 100)
    
    def __init__(self, display: Optional[DisplayBase] = None, mock: bool = True):
        """
        Initialize display manager.
        
        Args:
            display: DisplayBase instance (mock or real)
            mock: Use mock display if True
        """
        if display is None:
            self.display = MockDisplay() if mock else SPIDisplay()
        else:
            self.display = display
        
        self.width = self.display.width
        self.height = self.display.height
        self.current_state = "initial"
        self.last_update = 0
        self.last_block_time = 0
        self.on_state_change: Optional[Callable] = None
        
    def show_loading(self, message: str = "Loading..."):
        """Show loading screen."""
        self.display.clear()
        self.display.fill(self.COLOR_BLACK)
        
        # Center loading message
        y_center = self.height // 2
        self.display.text(message, self.width // 2, y_center, 
                         self.COLOR_YELLOW, size=2, centered=True)
        
        self.display.show()
        self.current_state = "loading"
        self._trigger_state_change()
    
    def show_connecting_wifi(self):
        """Show WiFi connection screen."""
        self.display.clear()
        self.display.fill(self.COLOR_BLACK)
        
        y = 50
        self.display.text("Connecting to WiFi...", 160, y, 
                         self.COLOR_BLUE, size=2, centered=True)
        y += 40
        self.display.text("SSID: ", 20, y, self.COLOR_WHITE)
        y += 20
        self.display.text("Please wait...", 160, y, 
                         self.COLOR_GRAY, size=1, centered=True)
        
        self.display.show()
        self.current_state = "connecting_wifi"
        self._trigger_state_change()
    
    def show_ap_mode(self, ip: str = "192.168.4.1"):
        """Show AP mode setup screen."""
        self.display.clear()
        self.display.fill(self.COLOR_BLACK)
        
        y = 30
        self.display.text("WiFi Setup", 160, y, self.COLOR_BLUE, 
                         size=2, centered=True)
        y += 50
        self.display.text("Connect to:", 20, y, self.COLOR_WHITE, size=1)
        y += 25
        self.display.text("CYD-Bitcoin", 160, y, self.COLOR_GREEN, 
                         size=2, centered=True)
        y += 50
        self.display.text("Then go to:", 20, y, self.COLOR_WHITE, size=1)
        y += 25
        self.display.text(ip, 160, y, self.COLOR_YELLOW, 
                         size=2, centered=True)
        y += 50
        self.display.text("Enter WiFi credentials", 160, y, 
                         self.COLOR_GRAY, size=1, centered=True)
        
        self.display.show()
        self.current_state = "ap_mode"
        self._trigger_state_change()
    
    def show_bitcoin_info(self, price: Optional[Dict[str, Any]] = None,
                         block: Optional[Dict[str, Any]] = None,
                         difficulty: Optional[Dict[str, Any]] = None,
                         local_time: Optional[str] = None):
        """
        Show Bitcoin information screen.
        
        Args:
            price: Bitcoin price data
            block: Latest block information
            difficulty: Mining difficulty data
            local_time: Current local time (SAST)
        """
        self.display.clear()
        self.display.fill(self.COLOR_BLACK)
        
        y = 5
        
        # Header with time
        if local_time:
            self.display.text(f"Bitcoin Info | {local_time}", 160, y,
                             self.COLOR_BLUE, size=1, centered=True)
        else:
            self.display.text("Bitcoin Information", 160, y,
                             self.COLOR_BLUE, size=1, centered=True)
        y += 20
        
        # Price section
        if price:
            usd = price.get('usd', 'N/A')
            self.display.text(f"BTC Price: ${usd}", 20, y,
                             self.COLOR_WHITE, size=1)
            y += 18
        
        # Block section
        if block:
            height = block.get('height', 'N/A')
            self.display.text(f"Block: #{height}", 20, y,
                             self.COLOR_GREEN, size=1)
            y += 18
            
            # Block hash (truncated)
            hash_full = block.get('hash', 'unknown')
            hash_short = hash_full[:16] + "..." if len(hash_full) > 16 else hash_full
            self.display.text(f"Hash: {hash_short}", 20, y,
                             self.COLOR_YELLOW, size=0, centered=False)
            y += 15
            
            # Miner
            miner = block.get('miner', 'Unknown')
            self.display.text(f"Miner: {miner}", 20, y,
                             self.COLOR_WHITE, size=0)
            y += 15
            
            # Transactions
            txs = block.get('transactions', 0)
            self.display.text(f"Transactions: {txs}", 20, y,
                             self.COLOR_WHITE, size=0)
            y += 18
        
        # Difficulty section
        if difficulty:
            diff = difficulty.get('difficulty', 'N/A')
            diff_display = f"{diff:.2e}" if isinstance(diff, float) else str(diff)
            self.display.text(f"Difficulty: {diff_display}", 20, y,
                             self.COLOR_YELLOW, size=0)
            y += 15
        
        # Time since last block
        if self.last_block_time > 0:
            elapsed = time.time() - self.last_block_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.display.text(f"Time since block: {minutes}m {seconds}s", 20, y,
                             self.COLOR_GREEN, size=0)
        
        self.display.show()
        self.current_state = "bitcoin_info"
        self.last_update = time.time()
        self._trigger_state_change()
    
    def show_error(self, error_msg: str, details: str = ""):
        """Show error screen."""
        self.display.clear()
        self.display.fill(self.COLOR_BLACK)
        
        y = 60
        self.display.text("ERROR", 160, y, self.COLOR_RED, 
                         size=2, centered=True)
        y += 50
        self.display.text(error_msg, 160, y, self.COLOR_WHITE, 
                         size=1, centered=True)
        y += 30
        if details:
            self.display.text(details, 160, y, self.COLOR_GRAY, 
                             size=0, centered=True)
        y += 30
        self.display.text("Please restart...", 160, y, 
                         self.COLOR_YELLOW, size=1, centered=True)
        
        self.display.show()
        self.current_state = "error"
        self._trigger_state_change()
    
    def show_offline(self, reason: str = "No WiFi"):
        """Show offline screen."""
        self.display.clear()
        self.display.fill(self.COLOR_BLACK)
        
        y = 80
        self.display.text("OFFLINE", 160, y, self.COLOR_RED, 
                         size=2, centered=True)
        y += 50
        self.display.text(reason, 160, y, self.COLOR_WHITE, 
                         size=1, centered=True)
        y += 40
        self.display.text("Attempting to reconnect...", 160, y, 
                         self.COLOR_GRAY, size=0, centered=True)
        
        self.display.show()
        self.current_state = "offline"
        self._trigger_state_change()
    
    def set_last_block_time(self, timestamp: float):
        """Set the time the last block was mined."""
        self.last_block_time = timestamp
    
    def register_state_change_callback(self, callback: Callable):
        """Register callback for state changes."""
        self.on_state_change = callback
    
    def _trigger_state_change(self):
        """Trigger state change callback if registered."""
        if self.on_state_change:
            try:
                self.on_state_change(self.current_state)
            except Exception as e:
                print(f"Error in state change callback: {e}")
