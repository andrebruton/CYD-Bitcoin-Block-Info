"""
Display Manager

Handles rendering to the ILI9341 LCD display (320x240).
Manages screen layout, text rendering, and updates.

For ESP32: Uses SPI interface to ILI9341
For PC testing: Mock display that prints to console
"""

from utils import (
    Colors, format_sast_time, format_time_ago, format_time_delta,
    format_price, format_thousands, format_hash, format_difficulty, seconds_since_block
)
import time


# Each pair of bytes encodes a stroke's endpoints as 0xXY in a 10x16 glyph.
_NUMERIC_FONT = {
    '0': b'\x21\x71\x12\x1d\x82\x8d\x2e\x7e\x12\x21\x71\x82\x1d\x2e\x8d\x7e',
    '1': b'\x22\x50\x50\x5e\x2e\x8e',
    '2': b'\x12\x21\x21\x71\x71\x82\x82\x86\x86\x1e\x1e\x8e',
    '3': b'\x11\x81\x82\x8d\x27\x87\x1e\x7e\x7e\x8d',
    '4': b'\x11\x18\x18\x88\x80\x8e',
    '5': b'\x11\x81\x11\x17\x17\x77\x77\x88\x88\x8d\x1e\x7e\x7e\x8d',
    '6': b'\x21\x71\x12\x1d\x17\x77\x77\x88\x88\x8d\x1d\x2e\x2e\x7e\x7e\x8d',
    '7': b'\x11\x81\x81\x3e',
    '8': b'\x21\x71\x12\x1d\x82\x8d\x27\x77\x2e\x7e\x12\x21\x71\x82\x1d\x2e\x8d\x7e',
    '9': b'\x21\x71\x12\x17\x82\x8d\x17\x28\x28\x88\x1e\x7e\x7e\x8d\x12\x21\x71\x82',
    '$': b'\x51\x5f\x22\x72\x13\x16\x16\x27\x27\x77\x77\x88\x88\x8c\x2d\x7d',
    '#': b'\x31\x3e\x71\x7e\x15\x95\x1a\x9a',
    '.': b'\x5d\x5e',
    '-': b'\x27\x77',
    ' ': b'',
}


class DisplayManager:
    """
    Manages the ILI9341 display (320x240).
    
    Provides methods to render Bitcoin data in a clean, readable layout.
    """
    
    def __init__(self, mock_mode=True, debug=False):
        """
        Initialize display manager.
        
        Args:
            mock_mode: Use console output instead of real display (for testing)
            debug: Print debug information
        """
        self.mock_mode = mock_mode
        self.debug = debug
        self.width = 320
        self.height = 240
        self._dashboard_active = False
        self._drawn_fields = {}
        
        # Current display data
        self.data = {
            'price': None,
            'block_height': None,
            'block_time': None,
            'block_hash': None,
            'difficulty': None,
            'tx_count': None,
            'fees': None,
            'loading': False,
            'error': None,
            'wifi_connected': None,
            'price_updated_at': None,
            'block_updated_at': None,
            'price_fresh': None,
            'block_fresh': None,
        }
        
        if not mock_mode:
            self._init_real_display()
        else:
            if debug:
                print("Display Manager initialized in MOCK mode")
    
    def _init_real_display(self):
        """Initialize real ILI9341 display via SPI."""
        try:
            from machine import Pin, SPI

            if self.debug:
                print("Attempting to initialize real ILI9341 display...")

            self.bl = Pin(21, Pin.OUT)
            self.bl.on()
            self.dc = Pin(2, Pin.OUT)
            self.cs = Pin(15, Pin.OUT)
            self.cs.on()
            self.spi = SPI(
                1,
                baudrate=40000000,
                polarity=0,
                phase=0,
                bits=8,
                firstbit=SPI.MSB,
                sck=Pin(14),
                mosi=Pin(13),
                miso=Pin(12),
            )

            self._init_ili9341()
            self._fill_screen(0x0000)

            if self.debug:
                print("ILI9341 display initialized on CYD HSPI")
        except Exception as e:
            print(f"Error initializing display: {e}")
            self.mock_mode = True  # Fall back to mock mode

    def _write_command(self, command):
        """Send one command byte to the ILI9341."""
        self.cs.off()
        self.dc.off()
        self.spi.write(bytes((command,)))
        self.cs.on()

    def _write_data(self, data):
        """Send data bytes to the ILI9341."""
        self.cs.off()
        self.dc.on()
        self.spi.write(data)
        self.cs.on()

    def _init_ili9341(self):
        """Configure the ILI9341 and wake the panel."""
        self._write_command(0x01)  # Software reset
        time.sleep(0.15)
        self._write_command(0x28)  # Display off during configuration

        init_commands = (
            (0xCF, (0x00, 0xC1, 0x30)),
            (0xED, (0x64, 0x03, 0x12, 0x81)),
            (0xE8, (0x85, 0x00, 0x78)),
            (0xCB, (0x39, 0x2C, 0x00, 0x34, 0x02)),
            (0xF7, (0x20,)),
            (0xEA, (0x00, 0x00)),
            (0xC0, (0x23,)),
            (0xC1, (0x10,)),
            (0xC5, (0x3E, 0x28)),
            (0xC7, (0x86,)),
            (0x36, (0x28,)),  # Landscape orientation, BGR color order
            (0x3A, (0x55,)),  # 16-bit RGB565 pixels
            (0xB1, (0x00, 0x18)),
            (0xB6, (0x08, 0x82, 0x27)),
            (0xF2, (0x00,)),
            (0x26, (0x01,)),
            (0xE0, (
                0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08, 0x4E, 0xF1,
                0x37, 0x07, 0x10, 0x03, 0x0E, 0x09, 0x00,
            )),
            (0xE1, (
                0x00, 0x0E, 0x14, 0x03, 0x11, 0x07, 0x31, 0xC1,
                0x48, 0x08, 0x0F, 0x0C, 0x31, 0x36, 0x0F,
            )),
        )
        for command, values in init_commands:
            self._write_command(command)
            self._write_data(bytes(values))

        self._write_command(0x11)  # Sleep out
        time.sleep(0.12)
        self._write_command(0x29)  # Display on
        time.sleep(0.02)

    def _set_address_window(self, x0, y0, x1, y1):
        """Select an inclusive pixel rectangle on the panel."""
        self._write_command(0x2A)
        self._write_data(bytes((
            (x0 >> 8) & 0xFF, x0 & 0xFF,
            (x1 >> 8) & 0xFF, x1 & 0xFF,
        )))
        self._write_command(0x2B)
        self._write_data(bytes((
            (y0 >> 8) & 0xFF, y0 & 0xFF,
            (y1 >> 8) & 0xFF, y1 & 0xFF,
        )))

    def _fill_screen(self, color):
        """Fill the panel with one RGB565 color using a small reusable buffer."""
        self._set_address_window(0, 0, self.width - 1, self.height - 1)
        self._write_command(0x2C)

        high = (color >> 8) & 0xFF
        low = color & 0xFF
        pixels = bytes((high, low)) * 128
        self.cs.off()
        self.dc.on()
        for _ in range((self.width * self.height) // 128):
            self.spi.write(pixels)
        self.cs.on()

    def _fill_rect(self, x, y, width, height, color):
        """Fill a rectangle without allocating a full-screen buffer."""
        self._set_address_window(x, y, x + width - 1, y + height - 1)
        self._write_command(0x2C)
        pixels = bytes(((color >> 8) & 0xFF, color & 0xFF)) * 128
        count = width * height
        self.cs.off()
        self.dc.on()
        for _ in range(count // 128):
            self.spi.write(pixels)
        if count % 128:
            self.spi.write(pixels[:(count % 128) * 2])
        self.cs.on()

    def _draw_text_region(self, x, y, width, text, color, background, scale=1, numeric=False):
        """Write an opaque text rectangle using a small monochrome buffer."""
        import framebuf

        font_width = width // scale
        font_height = 16 if numeric else 8
        buffer = bytearray(((font_width + 7) // 8) * font_height)
        framebuffer = framebuf.FrameBuffer(buffer, font_width, font_height, framebuf.MONO_HLSB)
        if numeric:
            if len(text) * 12 > font_width:
                raise ValueError("Numeric value does not fit its display field")
            for index, character in enumerate(text):
                strokes = _NUMERIC_FONT.get(character)
                if strokes is None:
                    raise ValueError(f"Unsupported numeric character: {character}")
                origin = index * 12
                for position in range(0, len(strokes), 2):
                    start, end = strokes[position], strokes[position + 1]
                    x0, y0 = origin + (start >> 4), start & 0x0F
                    x1, y1 = origin + (end >> 4), end & 0x0F
                    framebuffer.line(x0, y0, x1, y1, 1)
                    framebuffer.line(x0 + 1, y0, x1 + 1, y1, 1)
        else:
            framebuffer.text(text[:font_width // 8], 0, 0, 1)
        row_buffer = bytearray(width * 2)
        fg_high, fg_low = (color >> 8) & 0xFF, color & 0xFF
        bg_high, bg_low = (background >> 8) & 0xFF, background & 0xFF

        self._set_address_window(x, y, x + width - 1, y + font_height * scale - 1)
        self._write_command(0x2C)
        self.cs.off()
        self.dc.on()
        for row in range(font_height):
            for col in range(width):
                if framebuffer.pixel(col // scale, row):
                    row_buffer[col * 2] = fg_high
                    row_buffer[col * 2 + 1] = fg_low
                else:
                    row_buffer[col * 2] = bg_high
                    row_buffer[col * 2 + 1] = bg_low
            for _ in range(scale):
                self.spi.write(row_buffer)
        self.cs.on()

    def _draw_field(self, name, x, y, width, text, color, background, scale=1, numeric=False):
        """Redraw a fixed-size field only when its visible content changes."""
        value = (text, color, background, scale, numeric)
        if self._drawn_fields.get(name) != value:
            self._draw_text_region(x, y, width, text, color, background, scale, numeric)
            self._drawn_fields[name] = value

    def _draw_connection_indicator(self, color, background):
        """Draw the status circle only when its color changes."""
        if self._drawn_fields.get('connection_indicator') == color:
            return
        radius = 5
        self._set_address_window(301, 8, 311, 18)
        self._write_command(0x2C)
        self.cs.off()
        self.dc.on()
        foreground = bytes((color >> 8, color & 0xFF))
        backdrop = bytes((background >> 8, background & 0xFF))
        for y in range(-radius, radius + 1):
            row = bytearray()
            for x in range(-radius, radius + 1):
                row.extend(foreground if x * x + y * y <= radius * radius else backdrop)
            self.spi.write(row)
        self.cs.on()
        self._drawn_fields['connection_indicator'] = color

    def _draw_block_progress(self, remaining):
        """Update only the changed portion of the ten-minute reference bar."""
        width, x, y, height = 296, 12, 88, 10
        track, fill = 0x3186, 0xFD20
        filled = 0 if remaining is None else (width * remaining + 599) // 600
        previous = self._drawn_fields.get('block_progress')
        if previous is None:
            self._fill_rect(x, y, width, height, track)
            if filled:
                self._fill_rect(x, y, filled, height, fill)
        elif filled < previous:
            self._fill_rect(x + filled, y, previous - filled, height, track)
        elif filled > previous:
            self._fill_rect(x + previous, y, filled - previous, height, fill)
        self._drawn_fields['block_progress'] = filled

    def _draw_text_line(self, text, y, color):
        """Draw one 8-pixel-high text row using MicroPython's built-in font."""
        import framebuf

        buffer = bytearray(self.width)
        framebuffer = framebuf.FrameBuffer(buffer, self.width, 8, framebuf.MONO_HLSB)
        framebuffer.text(text[:40], 0, 0, 1)
        row_buffer = bytearray(self.width * 2)
        high, low = (color >> 8) & 0xFF, color & 0xFF

        self._set_address_window(0, y, self.width - 1, y + 7)
        self._write_command(0x2C)
        self.cs.off()
        self.dc.on()
        for row in range(8):
            for x in range(self.width):
                pixel = framebuffer.pixel(x, row)
                row_buffer[x * 2] = high if pixel else 0
                row_buffer[x * 2 + 1] = low if pixel else 0
            self.spi.write(row_buffer)
        self.cs.on()
    
    def render_full_screen(self, data):
        """
        Render complete screen with all data.
        
        Args:
            data: Dict with 'price', 'block', 'difficulty' keys
        """
        self.data.update({
            'price': data.get('price'),
            'loading': False,
            'error': None,
            'wifi_connected': data.get('wifi_connected'),
            'price_updated_at': data.get('price_updated_at'),
            'block_updated_at': data.get('block_updated_at'),
            'price_fresh': data.get('price_fresh'),
            'block_fresh': data.get('block_fresh'),
        })
        
        if data.get('block'):
            self.data.update({
                'block_height': data['block'].get('height'),
                'block_time': data['block'].get('time'),
                'block_hash': data['block'].get('hash'),
                'tx_count': data['block'].get('n_tx'),
            })
        
        if data.get('difficulty'):
            self.data['difficulty'] = data['difficulty']
        
        self._render()
    
    def show_loading(self, message="Loading..."):
        """Show loading indicator."""
        self.data['loading'] = True
        self.data['loading_message'] = message
        self.data['error'] = None
        self._render()
    
    def show_error(self, message):
        """Show error message."""
        self.data['error'] = message
        self.data['loading'] = False
        self._render()
    
    def show_wifi_setup(self):
        """Show WiFi setup screen (AP mode waiting)."""
        output = []
        output.append("+========================================+")
        output.append("|  CYD Bitcoin Setup                     |")
        output.append("+========================================+")
        output.append("|                                        |")
        output.append("|  WiFi Not Configured                  |")
        output.append("|  Please connect to:                   |")
        output.append("|                                        |")
        output.append("|  > CYDBitcoin                          |")
        output.append("|                                        |")
        output.append("|  Then visit:                           |")
        output.append("|  http://192.168.4.1                    |")
        output.append("|                                        |")
        output.append("|  (Waiting for connection...)           |")
        output.append("|                                        |")
        output.append("+========================================+")
        
        self._print_screen("\n".join(output))

    def show_setup_portal(self, ssid, password, address):
        """Show the temporary access point credentials and setup address."""
        lines = [
            "WIFI SETUP",
            "CONNECT TO:",
            ssid,
            "PASSWORD:",
            password,
            "OPEN IN BROWSER:",
            address,
        ]
        if self.mock_mode:
            self._print_screen("\n".join(lines))
        else:
            self._fill_screen(0x0000)
            self._dashboard_active = False
            self._drawn_fields.clear()
            for row, line in enumerate(lines):
                self._draw_text_line(line, row * 16, 0xFFFF)
            self._draw_connection_indicator(0xF800, 0x0000)
    
    def show_connecting(self, ssid, attempt, total_attempts, time_remaining, signal_strength=None):
        """
        Show WiFi connection progress screen.
        
        Args:
            ssid: WiFi network name
            attempt: Current attempt number
            total_attempts: Total attempts to make
            time_remaining: Seconds remaining
            signal_strength: Signal strength 0-100 (or None)
        """
        output = []
        output.append("+========================================+")
        output.append("|  Connecting to WiFi...                 |")
        output.append("+========================================+")
        
        # Network name (truncate if too long)
        ssid_short = ssid[:30] if len(ssid) <= 30 else ssid[:27] + "..."
        output.append(f"|  Network: {ssid_short:<27}|")
        
        # Signal strength bar
        if signal_strength is not None:
            bars = int(signal_strength / 10)
            bar = "█" * bars + "░" * (10 - bars)
            signal_line = f"|  Signal: {bar} ({signal_strength}%)|"
        else:
            signal_line = "|  Signal: ?                             |"
        output.append(signal_line)
        
        output.append("|                                        |")
        
        # Attempt counter
        attempt_line = f"|  Attempts: {attempt:3d}/{total_attempts:3d}".ljust(40) + "|"
        output.append(attempt_line)
        
        # Time remaining
        mins = time_remaining // 60
        secs = time_remaining % 60
        time_line = f"|  Time remaining: {mins}:{secs:02d}".ljust(40) + "|"
        output.append(time_line)
        
        output.append("|                                        |")
        output.append("|  (Don't unplug device)                 |")
        output.append("|                                        |")
        output.append("+========================================+")
        
        self._print_screen("\n".join(output))
    
    def show_wifi_connected(self, ssid, signal_strength=None):
        """
        Show WiFi connected success screen.
        
        Args:
            ssid: WiFi network name
            signal_strength: Signal strength 0-100 (or None)
        """
        output = []
        output.append("+========================================+")
        output.append("|  WiFi Connected!                       |")
        output.append("+========================================+")
        output.append("|                                        |")
        
        # Network name
        ssid_short = ssid[:30] if len(ssid) <= 30 else ssid[:27] + "..."
        output.append(f"|  Network: {ssid_short:<27}|")
        
        # Signal strength
        if signal_strength is not None:
            bars = int(signal_strength / 10)
            bar = "█" * bars + "░" * (10 - bars)
            signal_line = f"|  Signal: {bar} ({signal_strength}%)|"
        else:
            signal_line = "|  Signal: ?                             |"
        output.append(signal_line)
        
        # IP address
        from wifi_manager import WiFiManager
        wm = WiFiManager()
        ip = wm.get_ip_address()
        if ip:
            ip_line = f"|  IP: {ip:<31}|"
        else:
            ip_line = "|  IP: 192.168.1.x                      |"
        output.append(ip_line)
        
        output.append("|                                        |")
        output.append("|  Loading Bitcoin data...               |")
        output.append("|  (3 seconds)                           |")
        output.append("|                                        |")
        output.append("+========================================+")
        
        self._print_screen("\n".join(output))
    
    def show_connection_failed(self, ssid, error_message=""):
        """
        Show WiFi connection failed screen with reset option.
        
        Args:
            ssid: WiFi network name
            error_message: Error message to display
        """
        output = []
        output.append("+========================================+")
        output.append("|  WiFi Connection Failed                |")
        output.append("+========================================+")
        output.append("|                                        |")
        
        # Network name
        ssid_short = ssid[:30] if len(ssid) <= 30 else ssid[:27] + "..."
        output.append(f"|  Network: {ssid_short:<27}|")
        
        # Attempts
        output.append("|  Attempts: 300/300 (Timeout)           |")
        
        # Error message
        error_short = error_message[:32] if len(error_message) <= 32 else error_message[:29] + "..."
        error_line = f"|  Error: {error_short:<32}|"
        output.append(error_line)
        
        output.append("|                                        |")
        output.append("|  [  RESET WIFI  ]                      |")
        output.append("|                                        |")
        output.append("|  Tap button to reconfigure WiFi        |")
        output.append("|                                        |")
        output.append("+========================================+")
        
        self._print_screen("\n".join(output))
    
    def _print_screen(self, screen_text):
        """Print screen to console (helper method)."""
        try:
            print("\n" + screen_text)
        except UnicodeEncodeError:
            # Fallback for Windows console
            safe_screen = screen_text.encode('ascii', 'ignore').decode('ascii')
            print("\n" + safe_screen)
    
    def _render(self):
        """Internal render method."""
        if self.mock_mode:
            self._render_mock()
        else:
            self._render_real()
    
    def _render_mock(self):
        """Render to console (for testing)."""
        # Use simple ASCII characters for Windows compatibility
        output = []
        output.append("+========================================+")
        
        # Header: Price + Time
        if self.data['price']:
            price_str = f"BTC: ${self.data['price'].get('usd', 'N/A'):.2f}"
        else:
            price_str = "BTC: Loading..."
        
        time_str = format_sast_time()
        header = f"| {price_str:30s} {time_str:>6s}|"
        output.append(header)
        
        output.append("+========================================+")
        
        # Block info
        if self.data['block_height']:
            block_number = format_thousands(self.data['block_height'])
            block_str = f"| Block #{block_number:<30s}|"
            output.append(block_str)
            
            if self.data['block_time']:
                time_ago = format_time_ago(self.data['block_time'])
                seconds = seconds_since_block(self.data['block_time'])
                delta = format_time_delta(seconds) if seconds else "N/A"
                time_line = f"| {time_ago:20s} +{delta:>8s}|"
                output.append(time_line)
            
            if self.data['difficulty']:
                diff_str = format_difficulty(self.data['difficulty'])
                diff_line = f"| Difficulty: {diff_str:25s}|"
                output.append(diff_line)
        else:
            output.append("| Block: Loading...                      |")
        
        output.append("+========================================+")
        
        # Hash display
        if self.data['block_hash']:
            hash_short = format_hash(self.data['block_hash'])
            hash_line = f"| Hash: {hash_short:32s}|"
            output.append(hash_line)
        else:
            output.append("| Hash: Loading...                       |")
        
        output.append("+========================================+")
        
        # Stats
        if self.data['tx_count']:
            stats = f"| Txns: {str(self.data['tx_count']):<35s}|"
            output.append(stats)
        
        # Loading or error
        if self.data['loading']:
            output.append("| [Loading...]                           |")
        elif self.data['error']:
            error_line = f"| Error: {self.data['error'][:32]:<32s}|"
            output.append(error_line)
        else:
            output.append("| [Ready] [Refresh] [Menu]              |")
        
        output.append("+========================================+")
        
        # Print or update display
        try:
            print("\n".join(output))
        except UnicodeEncodeError:
            # Fallback for Windows console
            safe_output = []
            for line in output:
                # Remove any problematic unicode characters
                safe_line = line.encode('ascii', 'ignore').decode('ascii')
                safe_output.append(safe_line)
            print("\n".join(safe_output))
        
        if self.debug:
            print(f"Display rendered. Data: {self.data}")
    
    def _render_real(self):
        """Render to actual ILI9341 display."""
        background = 0x0841
        header = 0x10A3
        accent = 0xFD20
        white = 0xFFFF
        muted = 0xA514
        green = 0x07E0
        red = 0xF800

        if not self._dashboard_active:
            self._fill_screen(background)
            self._fill_rect(0, 0, 320, 28, header)
            self._fill_rect(0, 0, 4, 28, accent)
            self._fill_rect(12, 111, 296, 1, 0x3186)
            self._fill_rect(12, 224, 296, 1, 0x3186)
            self._drawn_fields.clear()
            self._dashboard_active = True

        field = self._draw_field
        field('title', 12, 10, 136, 'BITCOIN', accent, header)
        field('clock', 160, 10, 64, format_sast_time(), white, header)

        price = self.data['price'] or {}
        usd = price.get('usd')
        height = self.data['block_height']
        price_updated = self.data['price_updated_at']
        block_updated = self.data['block_updated_at']
        connected = self.data['wifi_connected']
        now = time.time()
        block_time = self.data['block_time']
        elapsed = seconds_since_block(block_time) if block_time is not None else None
        block_live = (
            height is not None and bool(self.data['block_hash']) and
            self.data['block_fresh'] is True and block_updated is not None and
            0 <= now - block_updated <= 180 and elapsed is not None and
            0 <= elapsed <= 1200
        )
        if not connected:
            indicator = red
        elif not block_live:
            indicator = accent
        else:
            indicator = 0x03E0 if int(now) % 5 == 0 else green
        self._draw_connection_indicator(indicator, header)
        if connected is False:
            status, status_color = 'OFFLINE', red
        elif self.data['error']:
            status, status_color = 'ERROR', red
        elif self.data['loading']:
            status, status_color = 'LOADING', accent
        elif not price or height is None:
            status, status_color = 'NO DATA', accent
        elif (
            price_updated is None or block_updated is None or
            now - min(price_updated, block_updated) > 180 or
            self.data['price_fresh'] is False or not block_live
        ):
            status, status_color = 'STALE', accent
        else:
            status, status_color = 'LIVE', green
        field('status', 232, 10, 64, status, status_color, header)

        field('usd_label', 12, 36, 144, 'BTC / USD', muted, background)
        usd_text = format_price(usd) if isinstance(usd, (int, float)) else '--'
        field('usd', 12, 49, 296, usd_text, white, background, numeric=True)
        if elapsed is None:
            remaining = None
            progress_label = '10 MIN REF  WAITING FOR BLOCK'
        elif elapsed < 0:
            remaining = None
            progress_label = '10 MIN REF  BLOCK TIME AHEAD'
        else:
            remaining = max(0, 600 - int(elapsed))
            if remaining:
                progress_label = f"10 MIN REF  {format_time_delta(remaining)} LEFT"
            else:
                progress_label = '10 MIN REF  TIME PASSED'
        field('progress_label', 12, 72, 296, progress_label, muted, background)
        self._draw_block_progress(remaining)

        field('block_label', 12, 119, 144, 'LATEST BLOCK', muted, background)
        block_text = f"#{format_thousands(height)}" if height is not None else '--'
        field('block', 12, 132, 160, block_text, white, background, numeric=True)
        if elapsed is not None and elapsed >= 0:
            elapsed_text = f"{format_time_delta(elapsed)} AGO"
        else:
            elapsed_text = '--'
        field('elapsed', 184, 136, 120, elapsed_text, accent, background)

        field('difficulty_label', 12, 157, 144, 'DIFFICULTY', muted, background)
        field('transactions_label', 168, 157, 136, 'TRANSACTIONS', muted, background)
        diff = self.data['difficulty']
        field('difficulty', 12, 170, 144, format_difficulty(diff), white, background)
        tx_count = self.data['tx_count']
        field('transactions', 168, 170, 136, str(tx_count) if tx_count is not None else '--',
              white, background)

        field('hash_label', 12, 187, 144, 'LAST BLOCK HASH', muted, background)
        block_hash = self.data['block_hash'] or ''
        field('hash_1', 12, 199, 296, block_hash[:32] or '--', white, background)
        field('hash_2', 12, 211, 296, block_hash[32:64], white, background)

        if self.data['loading']:
            footer = self.data.get('loading_message', 'Loading...')
        elif self.data['error']:
            footer = f"ERROR: {self.data['error']}"
        elif price_updated is not None and block_updated is not None:
            updated = time.gmtime(min(price_updated, block_updated) + 7200)
            footer = f"OLDEST UPDATE {updated[3]:02d}:{updated[4]:02d} SAST"
        else:
            footer = 'WAITING FOR DATA'
        field('footer', 12, 229, 296, footer, muted, background)
    
    def clear_screen(self):
        """Clear display."""
        if self.mock_mode:
            print("\n" * 50)  # Simulate clearing
        else:
            self._fill_screen(0x0000)
            self._dashboard_active = False
            self._drawn_fields.clear()
    
    def test_display(self):
        """Test display rendering with sample data."""
        test_data = {
            'price': {'usd': 45320.50},
            'block': {
                'height': 863452,
                'time': 1700500000,  # Unix timestamp (past)
                'hash': '0a3f7e2c1b4a8f9e3d5c6b7a8f9e0d1c2b3a4f5e6d7c8b9a0e1d2f3c4a5b6',
                'n_tx': 2847,
            },
            'difficulty': 84.2e12,
        }
        
        print("Testing display rendering...")
        self.render_full_screen(test_data)
        
        print("\nTesting loading state...")
        self.show_loading("Fetching block data...")
        
        print("\nTesting error state...")
        self.show_error("API timeout")


# For testing
if __name__ == '__main__':
    display = DisplayManager(mock_mode=True, debug=True)
    display.test_display()
