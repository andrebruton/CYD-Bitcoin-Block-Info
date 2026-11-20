"""
Boot Sequence

Entry point for ESP32 CYD Bitcoin application.
Handles WiFi setup and connection before launching main app.

Boot flow:
1. Check for saved WiFi credentials
2. If not found: Start AP mode and web server for setup
3. If found: Try to connect to saved WiFi
4. After successful connection: Launch main Bitcoin app
5. On timeout: Show reset option
"""

import time
import sys


def boot():
    """
    Main boot sequence.
    
    Returns:
        True if should proceed to main app, False to exit
    """
    
    # Import after adding src to path (for PC testing)
    sys.path.insert(0, 'src')
    
    from wifi_manager import WiFiManager
    from wifi_web_server import WiFiWebServer
    from display_manager import DisplayManager
    
    # Initialize
    wifi_manager = WiFiManager(debug=True)
    display = DisplayManager(mock_mode=False, debug=True)
    
    print("\n" + "="*50)
    print("CYD BITCOIN - BOOT SEQUENCE")
    print("="*50 + "\n")
    
    # Show splash
    display.show_loading("CYD Bitcoin\nBooting...")
    time.sleep(2)
    
    # Check for saved WiFi credentials
    print("[Boot] Checking saved WiFi credentials...")
    credentials = wifi_manager.load_credentials()
    
    if not credentials:
        # First boot - no saved WiFi
        print("[Boot] No saved WiFi found. Starting setup mode...")
        return _handle_ap_mode(wifi_manager, display)
    else:
        # Returning user - try to connect to saved WiFi
        print(f"[Boot] Found saved WiFi: {credentials['ssid']}")
        return _handle_connection(wifi_manager, display, credentials)


def _handle_ap_mode(wifi_manager, display):
    """
    Handle WiFi setup mode (Access Point).
    
    Args:
        wifi_manager: WiFiManager instance
        display: DisplayManager instance
    
    Returns:
        True when WiFi is configured and device should restart
    """
    
    from wifi_web_server import WiFiWebServer
    
    # Start AP mode
    print("[AP Mode] Starting Access Point...")
    if not wifi_manager.start_ap_mode("CYDBitcoin", "12345678"):
        print("[AP Mode] Failed to start AP mode")
        display.show_error("AP Mode Failed")
        return False
    
    # Show setup screen on display
    display.show_wifi_setup()
    
    # Start web server
    ws = WiFiWebServer(wifi_manager, debug=True)
    if not ws.start():
        print("[WebServer] Failed to start web server")
        display.show_error("WebServer Failed")
        return False
    
    print("[AP Mode] Waiting for WiFi setup...")
    print("[AP Mode] Access point: CYDBitcoin")
    print("[AP Mode] Visit: http://192.168.4.1")
    
    # Wait for user to submit form
    timeout = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Handle web requests
        result = ws.handle_request()
        
        if result and result.get('ssid') and result.get('password'):
            # Credentials received!
            print(f"[AP Mode] WiFi configured: {result['ssid']}")
            display.show_loading("WiFi Configured\nRestarting...")
            time.sleep(2)
            
            # Restart
            import machine
            machine.reset()
            return True
        
        # Small delay to prevent busy loop
        time.sleep(0.1)
    
    # Timeout
    print("[AP Mode] Setup timeout")
    ws.stop()
    display.show_error("Setup Timeout")
    return False


def _handle_connection(wifi_manager, display, credentials):
    """
    Handle WiFi connection (returning user).
    
    Args:
        wifi_manager: WiFiManager instance
        display: DisplayManager instance
        credentials: Dict with 'ssid' and 'password'
    
    Returns:
        True if connected and ready for main app, False on timeout
    """
    
    ssid = credentials['ssid']
    password = credentials['password']
    timeout = 300  # 5 minutes
    
    print(f"[Connection] Connecting to {ssid}...")
    
    # Try to connect
    for status in wifi_manager.connect_to_wifi(ssid, password, timeout=timeout):
        
        if status['status'] == 'connected':
            # Success!
            ip = wifi_manager.get_ip_address()
            print(f"[Connection] Connected! IP: {ip}")
            
            # Show connected screen
            display.show_wifi_connected(ssid, status.get('signal_strength'))
            time.sleep(3)
            
            return True
        
        elif status['status'] == 'connecting':
            # Still trying
            remaining = status.get('time_remaining', 0)
            attempt = status.get('attempt', 0)
            total = status.get('total_attempts', 0)
            signal = status.get('signal_strength')
            
            print(f"[Connection] Attempt {attempt}/{total}, Signal: {signal}%, Remaining: {remaining}s")
            
            # Update display
            display.show_connecting(ssid, attempt, total, remaining, signal)
        
        elif status['status'] == 'failed':
            # Failed to connect
            error = status.get('error', 'Unknown error')
            print(f"[Connection] Connection failed: {error}")
            
            # Show failed screen with reset option
            display.show_connection_failed(ssid, error)
            
            # Wait for reset or user action
            # For now, just show the screen and exit
            # (In real app, would wait for button press)
            print("[Connection] Waiting for reset...")
            time.sleep(5)
            
            return False
    
    return False


def handle_reset():
    """
    Handle reset WiFi request.
    
    This is called if WiFi connection fails and user presses reset.
    Clears credentials and restarts boot sequence.
    """
    
    from wifi_manager import WiFiManager
    
    wifi_manager = WiFiManager(debug=True)
    
    print("[Reset] Clearing WiFi credentials...")
    wifi_manager.clear_credentials()
    
    print("[Reset] Restarting boot sequence...")
    time.sleep(2)
    
    import machine
    machine.reset()


if __name__ == '__main__':
    # Run boot sequence
    result = boot()
    
    if result:
        print("\n[Boot] WiFi ready. Starting main application...\n")
        
        # Import and run main app
        try:
            from main import BitcoinApp
            app = BitcoinApp()
            app.run()
        except KeyboardInterrupt:
            print("\n[Boot] Application stopped")
    else:
        print("\n[Boot] Boot sequence failed")
