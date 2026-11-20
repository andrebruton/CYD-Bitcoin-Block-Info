"""Tests for incremental rendering on the CYD display."""

import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import display_manager
from display_manager import DisplayManager


def make_dashboard(monkeypatch):
    display = DisplayManager(mock_mode=True)
    display.mock_mode = False
    display._fill_screen = Mock()
    display._fill_rect = Mock()
    display._draw_text_region = Mock()
    display._draw_connection_indicator = Mock()
    monkeypatch.setattr(display_manager, 'format_sast_time', lambda: '16:06')
    monkeypatch.setattr(display_manager, 'seconds_since_block', lambda timestamp: 154)
    monkeypatch.setattr(display_manager.time, 'time', lambda: 1000)
    data = {
        'price': {'usd': 61420.50},
        'block': {
            'height': 976731,
            'time': 100,
            'hash': 'a' * 64,
            'n_tx': 2981,
        },
        'difficulty': 134.8e12,
        'wifi_connected': True,
        'price_updated_at': 990,
        'block_updated_at': 990,
        'price_fresh': True,
        'block_fresh': True,
    }
    return display, data


def test_redraws_only_changed_field_and_preserves_full_width(monkeypatch):
    display, data = make_dashboard(monkeypatch)
    display.render_full_screen(data)
    display._fill_screen.assert_called_once()
    assert display._drawn_fields['usd'][0] == '$61 420.50'
    assert display._drawn_fields['block'][0] == '#976 731'
    assert display._drawn_fields['hash_1'][0] == 'a' * 32
    assert display._drawn_fields['hash_2'][0] == 'a' * 32
    display._draw_text_region.reset_mock()

    display.render_full_screen(data)
    display._draw_text_region.assert_not_called()

    data['price'] = {'usd': 99.0}
    display.render_full_screen(data)
    display._draw_text_region.assert_called_once()
    x, y, width, text, _, _, scale, numeric = display._draw_text_region.call_args.args
    assert (x, y, width, text, scale, numeric) == (12, 49, 296, '$99.00', 1, True)
    display._fill_screen.assert_called_once()


@pytest.mark.parametrize(
    'height, expected', [(999, '#999'), (1000000, '#1 000 000')]
)
def test_block_height_thousands_are_grouped_without_full_redraw(monkeypatch, height, expected):
    display, data = make_dashboard(monkeypatch)
    display.render_full_screen(data)
    display._draw_text_region.reset_mock()
    data['block']['height'] = height

    display.render_full_screen(data)

    display._draw_text_region.assert_called_once()
    assert display._draw_text_region.call_args.args[3] == expected
    assert display._draw_text_region.call_args.args[2] == 160
    display._fill_screen.assert_called_once()


def test_status_tracks_failure_offline_and_recovery(monkeypatch):
    display, data = make_dashboard(monkeypatch)
    display.render_full_screen(data)
    assert display._drawn_fields['status'][0] == 'LIVE'

    data['price_fresh'] = False
    display.render_full_screen(data)
    assert display._drawn_fields['status'][0] == 'STALE'

    data['wifi_connected'] = False
    display.render_full_screen(data)
    assert display._drawn_fields['status'][0] == 'OFFLINE'

    data['wifi_connected'] = True
    data['price_fresh'] = True
    display.render_full_screen(data)
    assert display._drawn_fields['status'][0] == 'LIVE'

    data['block_updated_at'] = 800
    display.render_full_screen(data)
    assert display._drawn_fields['status'][0] == 'STALE'


@pytest.mark.parametrize(
    'connected, fresh, updated, elapsed, expected',
    [
        (None, True, 990, 154, 0xF800),
        (False, True, 990, 154, 0xF800),
        (True, False, 990, 154, 0xFD20),
        (True, None, None, 154, 0xFD20),
        (True, True, 819, 154, 0xFD20),
        (True, True, 820, 1200, 0x03E0),
        (True, True, 990, 1201, 0xFD20),
        (True, True, 990, -1, 0xFD20),
    ],
)
def test_connection_indicator_states(monkeypatch, connected, fresh, updated, elapsed, expected):
    display, data = make_dashboard(monkeypatch)
    monkeypatch.setattr(display_manager, 'seconds_since_block', lambda timestamp: elapsed)
    data.update(wifi_connected=connected, block_fresh=fresh, block_updated_at=updated)

    display.render_full_screen(data)

    display._draw_connection_indicator.assert_called_with(expected, 0x10A3)


def test_live_indicator_pulses_only_with_valid_block(monkeypatch):
    display, data = make_dashboard(monkeypatch)
    clock = [1001]
    monkeypatch.setattr(display_manager.time, 'time', lambda: clock[0])

    display.render_full_screen(data)
    display._draw_connection_indicator.assert_called_with(0x07E0, 0x10A3)
    clock[0] = 1005
    display.render_full_screen(data)
    display._draw_connection_indicator.assert_called_with(0x03E0, 0x10A3)
    clock[0] = 1006
    display.render_full_screen(data)
    display._draw_connection_indicator.assert_called_with(0x07E0, 0x10A3)

    data['block']['hash'] = None
    display.render_full_screen(data)
    display._draw_connection_indicator.assert_called_with(0xFD20, 0x10A3)
    clock[0] = 1010
    display.render_full_screen(data)
    display._draw_connection_indicator.assert_called_with(0xFD20, 0x10A3)


def test_connection_circle_draws_only_when_color_changes():
    display = DisplayManager(mock_mode=True)
    display._set_address_window = Mock()
    display._write_command = Mock()
    display.cs = Mock()
    display.dc = Mock()
    rows = []
    display.spi = Mock()
    display.spi.write.side_effect = lambda value: rows.append(bytes(value))

    display._draw_connection_indicator(0xF800, 0x10A3)
    display._set_address_window.assert_called_once_with(301, 8, 311, 18)
    assert len(rows) == 11
    assert rows[0] == b'\x10\xa3' * 5 + b'\xf8\x00' + b'\x10\xa3' * 5
    assert rows[5] == b'\xf8\x00' * 11

    display._draw_connection_indicator(0xF800, 0x10A3)
    assert len(rows) == 11
    display._draw_connection_indicator(0xFD20, 0x10A3)
    assert len(rows) == 22
    assert rows[16] == b'\xfd\x20' * 11


def test_clear_invalidates_cached_fields(monkeypatch):
    display, data = make_dashboard(monkeypatch)
    display.render_full_screen(data)
    display.clear_screen()
    display._draw_text_region.reset_mock()

    display.render_full_screen(data)
    assert display._draw_text_region.call_count > 1
    assert display._fill_screen.call_count == 3


@pytest.mark.parametrize(
    'elapsed, expected_width, expected_label',
    [
        (0, 296, '10 MIN REF  10:00 LEFT'),
        (300, 148, '10 MIN REF  5:00 LEFT'),
        (599, 1, '10 MIN REF  0:01 LEFT'),
        (600, 0, '10 MIN REF  TIME PASSED'),
        (900, 0, '10 MIN REF  TIME PASSED'),
        (-1, 0, '10 MIN REF  BLOCK TIME AHEAD'),
    ],
)
def test_block_progress_bounds(monkeypatch, elapsed, expected_width, expected_label):
    display, data = make_dashboard(monkeypatch)
    monkeypatch.setattr(display_manager, 'seconds_since_block', lambda timestamp: elapsed)

    display.render_full_screen(data)

    assert display._drawn_fields['block_progress'] == expected_width
    assert display._drawn_fields['progress_label'][0] == expected_label
    assert display._drawn_fields['status'][0] == ('STALE' if elapsed < 0 else 'LIVE')


def test_progress_missing_time_and_new_block(monkeypatch):
    display, data = make_dashboard(monkeypatch)
    monkeypatch.setattr(display_manager, 'seconds_since_block', lambda timestamp: timestamp)
    data['block']['time'] = None
    display.render_full_screen(data)
    assert display._drawn_fields['block_progress'] == 0
    assert display._drawn_fields['progress_label'][0] == '10 MIN REF  WAITING FOR BLOCK'

    data['block']['time'] = 300
    display.render_full_screen(data)
    assert display._drawn_fields['block_progress'] == 148
    display._fill_rect.reset_mock()

    data['block']['time'] = 310
    display.render_full_screen(data)
    display._fill_rect.assert_called_once_with(156, 88, 4, 10, 0x3186)
    display._fill_rect.reset_mock()

    data['block']['time'] = 0
    display.render_full_screen(data)
    display._fill_rect.assert_called_once_with(156, 88, 152, 10, 0xFD20)
    display._fill_screen.assert_called_once()


def test_text_region_streams_opaque_scaled_pixels(monkeypatch):
    class FrameBuffer:
        def __init__(self, buffer, width, height, format):
            pass

        def text(self, text, x, y, color):
            pass

        def pixel(self, x, y):
            return x == 0 and y == 0

    framebuf = Mock(MONO_HLSB=1, FrameBuffer=FrameBuffer)
    monkeypatch.setitem(sys.modules, 'framebuf', framebuf)
    display = DisplayManager(mock_mode=True)
    display._set_address_window = Mock()
    display._write_command = Mock()
    display.cs = Mock()
    display.dc = Mock()
    rows = []
    display.spi = Mock()
    display.spi.write.side_effect = lambda value: rows.append(bytes(value))

    display._draw_text_region(12, 10, 16, 'A', 0xFFFF, 0x1234, 2)

    display._set_address_window.assert_called_once_with(12, 10, 27, 25)
    assert len(rows) == 16
    assert rows[0] == rows[1] == b'\xff\xff' * 2 + b'\x12\x34' * 14
    assert rows[2] == b'\x12\x34' * 16


def test_numeric_font_draws_complete_block_height(monkeypatch):
    class FrameBuffer:
        def __init__(self, buffer, width, height, format):
            self.pixels = set()

        def line(self, x0, y0, x1, y1, color):
            steps = max(abs(x1 - x0), abs(y1 - y0))
            for step in range(steps + 1):
                if steps:
                    x = x0 + round((x1 - x0) * step / steps)
                    y = y0 + round((y1 - y0) * step / steps)
                else:
                    x, y = x0, y0
                self.pixels.add((x, y))

        def pixel(self, x, y):
            return (x, y) in self.pixels

    monkeypatch.setitem(sys.modules, 'framebuf', Mock(MONO_HLSB=1, FrameBuffer=FrameBuffer))
    display = DisplayManager(mock_mode=True)
    display._set_address_window = Mock()
    display._write_command = Mock()
    display.cs = Mock()
    display.dc = Mock()
    rows = []
    display.spi = Mock()
    display.spi.write.side_effect = lambda value: rows.append(bytes(value))

    text = '#1 000 000'
    display._draw_text_region(12, 132, 160, text, 0xFFFF, 0x0841, numeric=True)

    display._set_address_window.assert_called_once_with(12, 132, 171, 147)
    assert len(rows) == 16
    for index in range(len(text)):
        start, end = index * 24, (index + 1) * 24
        if text[index] == ' ':
            assert all(row[start:end] == b'\x08\x41' * 12 for row in rows)
        else:
            assert any(b'\xff\xff' in row[start:end] for row in rows)
    assert all(row[len(text) * 24:] == b'\x08\x41' * (160 - len(text) * 12)
               for row in rows)

    rows.clear()
    display._draw_text_region(12, 49, 296, '$61 420.50', 0xFFFF, 0x0841, numeric=True)
    assert all(row[72:96] == b'\x08\x41' * 12 for row in rows)
    assert any(b'\xff\xff' in row[96:120] for row in rows)

    with pytest.raises(ValueError, match='does not fit'):
        display._draw_text_region(12, 132, 160, '#' + '1' * 13, 0xFFFF, 0, numeric=True)
