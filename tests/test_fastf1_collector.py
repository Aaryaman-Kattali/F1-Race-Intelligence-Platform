"""
Tests for the FastF1 data collector module.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_collectors.fastf1_collector import FastF1Collector


class TestFastF1Collector:
    def test_collect_race_weekend_data_extracts_weather_correctly(self):
        """
        Verify that _collect_race_weekend_data correctly reuses the weather data
        extracted inside _get_session_data, rather than trying to extract it again
        from the returned session dictionary (which causes silent failure).
        """
        collector = FastF1Collector()
        
        # Mock the internal methods called by _collect_race_weekend_data
        with patch.object(collector, '_get_session_data') as mock_get_session, \
             patch.object(collector, '_extract_driver_data') as mock_extract_driver, \
             patch.object(collector, '_extract_race_winner') as mock_extract_winner:
             
            # Simulate _get_session_data returning a valid dictionary with weather
            def mock_session_side_effect(year, race_round, session_type):
                if session_type == 'Race':
                    return {
                        'session_type': 'Race',
                        'weather': {'available': True, 'air_temp_avg': 25.0}
                    }
                return None
                
            mock_get_session.side_effect = mock_session_side_effect
            mock_extract_winner.return_value = 'VER'
            mock_extract_driver.return_value = {}
            
            result = collector._collect_race_weekend_data(2024, 1, 'Test Circuit')
            
            assert result is not None
            assert 'weather' in result
            assert result['weather']['available'] is True
            assert result['weather']['air_temp_avg'] == 25.0
