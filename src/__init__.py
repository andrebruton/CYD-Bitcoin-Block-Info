"""
CYD Bitcoin Project - Phased Development

This package contains code for displaying real-time Bitcoin information
on the Cheap Yellow Display (CYD) ESP32 board.

Phases:
- Phase 1: Basic Bitcoin information display
- Phase 2: WiFi setup and credential management
- Phase 3: Display manager and Bitcoin data fetching

Main components:
- wifi/: WiFi connection management
- bitcoin/: Bitcoin data fetching and APIs
- display/: Display management and rendering
- app.py: Main application controller

Usage:
    from src.app import AppController
    from src.display.manager import DisplayManager
    
    display = DisplayManager(mock=True)
    app = AppController(display_manager=display)
    app.start()
"""

__version__ = "0.3.0"
__author__ = "CYD Bitcoin Project"
__all__ = ["AppController", "DisplayManager", "WiFiManager", "BitcoinFetcher"]
