"""
WiFi Web Server

Simple HTTP server for WiFi setup at 192.168.4.1.
Serves HTML form for entering WiFi credentials.
"""

class WiFiWebServer:
    """
    Simple HTTP web server for WiFi setup.
    
    Runs on 192.168.4.1 (AP mode) and serves:
    - GET /: HTML form for entering WiFi SSID and password
    - POST /save: Accept form submission and save credentials
    """
    
    def __init__(self, wifi_manager, port=80, debug=False):
        """
        Initialize web server.
        
        Args:
            wifi_manager: WiFiManager instance
            port: HTTP port (usually 80)
            debug: Print debug information
        """
        self.wifi_manager = wifi_manager
        self.port = port
        self.debug = debug
        self.server = None
        self.socket = None
        self.running = False
    
    def _get_html_form(self):
        """
        Generate HTML form for WiFi setup.
        
        Returns:
            HTML string (kept minimal to save memory)
        """
        html = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CYD Setup</title>
<style>
body { font-family: Arial, sans-serif; padding: 20px; background: #f0f0f0; }
.container { max-width: 400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
h1 { color: #f7931a; text-align: center; margin: 0 0 20px 0; font-size: 24px; }
label { display: block; margin: 15px 0 5px 0; font-weight: bold; color: #333; }
input { width: 100%; padding: 10px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; font-size: 14px; }
input:focus { outline: none; border-color: #f7931a; }
button { width: 100%; padding: 12px; background: #f7931a; color: white; border: none; border-radius: 4px; font-size: 16px; font-weight: bold; cursor: pointer; }
button:hover { background: #e68b1a; }
.info { color: #666; font-size: 12px; margin-top: 20px; text-align: center; }
</style>
</head>
<body>
<div class="container">
<h1>CYD Bitcoin Setup</h1>
<form method="POST" action="/save">
<label for="ssid">WiFi Network Name:</label>
<input type="text" id="ssid" name="ssid" placeholder="Enter WiFi SSID" required autofocus>
<label for="password">WiFi Password:</label>
<input type="password" id="password" name="password" placeholder="Enter password" required>
<button type="submit">Connect Device</button>
</form>
<div class="info">
<p>Your device will connect to this WiFi network and display Bitcoin information.</p>
</div>
</div>
</body>
</html>"""
        return html
    
    def start(self):
        """
        Start the web server.
        
        Returns:
            True if successful, False otherwise
        """
        # Try to import socket module (ESP32 MicroPython)
        try:
            import socket
            self.socket = socket
        except ImportError:
            if self.debug:
                print("[WebServer] Mock mode (no socket module)")
            return True  # Mock mode
        
        try:
            # Create socket and bind to port
            sock = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_STREAM)
            sock.setsockopt(self.socket.SOL_SOCKET, self.socket.SO_REUSEADDR, 1)
            sock.bind(('', self.port))
            sock.listen(1)
            sock.settimeout(1.0)
            
            self.server = sock
            self.running = True
            
            if self.debug:
                print(f"[WebServer] Started on http://192.168.4.1:{self.port}")
            
            return True
        
        except Exception as e:
            if self.debug:
                print(f"[WebServer] Error starting: {e}")
            return False
    
    def handle_request(self):
        """
        Handle one HTTP request.
        
        Returns:
            Dict with request info, or None if no request
            {
                'method': 'GET'|'POST',
                'path': request path,
                'ssid': ssid (if POST),
                'password': password (if POST),
                'error': error message (if any)
            }
        """
        if not self.running or not self.server:
            return None
        
        client = None
        try:
            client, _ = self.server.accept()
            client.settimeout(5)
            request = b''
            while b'\r\n\r\n' not in request:
                chunk = client.recv(512)
                if not chunk or len(request) + len(chunk) > 4096:
                    raise ValueError("Invalid or oversized request headers")
                request += chunk

            headers, body = request.split(b'\r\n\r\n', 1)
            lines = headers.decode('ascii').split('\r\n')
            parts = lines[0].split()
            if len(parts) != 3:
                raise ValueError("Invalid request line")
            method, path = parts[:2]

            if method == 'GET' and path == '/':
                self._respond(client, '200 OK', self._get_html_form())
                return {'method': method, 'path': path}

            if method == 'POST' and path == '/save':
                length = None
                for line in lines[1:]:
                    name, separator, value = line.partition(':')
                    if separator and name.lower() == 'content-length':
                        length = int(value.strip())
                if length is None or length < 0 or length > 1024:
                    raise ValueError("Invalid content length")
                while len(body) < length:
                    chunk = client.recv(min(512, length - len(body)))
                    if not chunk:
                        raise ValueError("Incomplete form")
                    body += chunk

                fields = {}
                for param in body[:length].split(b'&'):
                    key, separator, value = param.partition(b'=')
                    if separator:
                        fields[self._decode_form_value(key)] = self._decode_form_value(value)
                ssid = fields.get('ssid')
                password = fields.get('password')
                if not ssid or not password:
                    raise ValueError("SSID and password are required")
                if not self.wifi_manager.save_credentials(ssid, password):
                    self._respond(client, '500 Internal Server Error', 'Could not save credentials')
                    return {'error': 'Could not save credentials'}

                self._respond(client, '200 OK', 'WiFi saved. The device is connecting.')
                return {'method': method, 'path': path, 'saved': True}

            self._respond(client, '404 Not Found', 'Not found')
            return {'method': method, 'path': path, 'error': 'Not found'}
        except ValueError as e:
            print(f"[WebServer] Invalid request: {e}")
            if client:
                self._respond(client, '400 Bad Request', 'Invalid request')
            return None
        except OSError as e:
            if client is not None or not e.args or e.args[0] not in (110, 116):
                print(f"[WebServer] Request error: {e}")
            return None
        finally:
            if client:
                client.close()

    def _respond(self, client, status, body):
        """Send a complete HTTP response."""
        body = body.encode('utf-8')
        header = (
            f"HTTP/1.1 {status}\r\nContent-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
        )
        client.sendall(header.encode('ascii') + body)

    def _decode_form_value(self, value):
        """Decode a URL-encoded form field as UTF-8."""
        result = bytearray()
        index = 0
        while index < len(value):
            char = value[index]
            if char == 37:
                if index + 2 >= len(value):
                    raise ValueError("Invalid percent escape")
                result.append(int(value[index + 1:index + 3], 16))
                index += 3
            else:
                result.append(32 if char == 43 else char)
                index += 1
        return result.decode('utf-8')
    
    def stop(self):
        """Stop the web server."""
        self.running = False
        if self.server:
            try:
                self.server.close()
            except Exception:
                pass
        if self.debug:
            print("[WebServer] Stopped")


# For testing
if __name__ == '__main__':
    # Mock WiFi manager for testing
    class MockWiFiManager:
        def __init__(self):
            self.saved_ssid = None
            self.saved_password = None
        
        def save_credentials(self, ssid, password):
            self.saved_ssid = ssid
            self.saved_password = password
            print(f"Mock: Saved {ssid}")
            return True
    
    wm = MockWiFiManager()
    ws = WiFiWebServer(wm, debug=True)
    
    # Test: Get HTML
    html = ws._get_html_form()
    print(f"HTML form size: {len(html)} bytes")
    print(f"First 100 chars: {html[:100]}")
    
    # Test: Start server (will fail without socket in this mock)
    result = ws.start()
    print(f"Server start: {result}")
