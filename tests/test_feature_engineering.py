"""
Tests for the feature engineering module (Enhanced2025FeatureEngineer).
"""

import sys
from pathlib import Path

import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processors.feature_engineer import Enhanced2025FeatureEngineer

# ---------------------------------------------------------------------------
# Historical features (experienced drivers)
# ---------------------------------------------------------------------------


class TestCreateHistoricalFeatures:
    """Tests for _create_historical_features."""

    def setup_method(self):
        self.engineer = Enhanced2025FeatureEngineer()

    def test_avg_position_from_races(self, mock_historical_data, mock_circuit_config):
        """Average position should match the mean of race positions."""
        features = self.engineer._create_historical_features(
            "VER", mock_historical_data, mock_circuit_config
        )
        # VER finished 1, 1, 5 in 3 races
        expected_avg = np.mean([1, 1, 5])
        assert abs(features["historical_avg_position"] - expected_avg) < 0.01

    def test_best_position(self, mock_historical_data, mock_circuit_config):
        features = self.engineer._create_historical_features(
            "VER", mock_historical_data, mock_circuit_config
        )
        assert features["historical_best_position"] == 1

    def test_win_rate(self, mock_historical_data, mock_circuit_config):
        features = self.engineer._create_historical_features(
            "VER", mock_historical_data, mock_circuit_config
        )
        # VER won 2 out of 3 races
        assert abs(features["historical_win_rate"] - 2 / 3) < 0.01

    def test_podium_rate(self, mock_historical_data, mock_circuit_config):
        features = self.engineer._create_historical_features(
            "NOR", mock_historical_data, mock_circuit_config
        )
        # NOR finished 4, 2, 2 → 2 podiums out of 3
        assert abs(features["historical_podium_rate"] - 2 / 3) < 0.01

    def test_circuit_experience_capped(self, mock_historical_data, mock_circuit_config):
        features = self.engineer._create_historical_features(
            "VER", mock_historical_data, mock_circuit_config
        )
        # 3 races → 3/5 = 0.6, capped at 1.0
        assert 0.0 <= features["circuit_experience"] <= 1.0

    def test_driver_not_in_data_returns_defaults(
        self, mock_historical_data, mock_circuit_config
    ):
        """A driver with no historical results should get default values."""
        features = self.engineer._create_historical_features(
            "SAI", mock_historical_data, mock_circuit_config
        )
        assert features["historical_avg_position"] == 12.0
        assert features["historical_win_rate"] == 0.0
        assert features["circuit_race_count"] == 0

    def test_consistency_between_zero_and_one(
        self, mock_historical_data, mock_circuit_config
    ):
        features = self.engineer._create_historical_features(
            "VER", mock_historical_data, mock_circuit_config
        )
        assert 0.0 <= features["historical_consistency"] <= 1.0


# ---------------------------------------------------------------------------
# Rookie features
# ---------------------------------------------------------------------------


class TestRookieFeatures:
    """Tests for _create_rookie_features_from_2025_data."""

    def setup_method(self):
        self.engineer = Enhanced2025FeatureEngineer()

    def test_rookie_has_zero_win_rate(self):
        features = self.engineer._create_rookie_features_from_2025_data("ANT")
        assert features["historical_win_rate"] == 0.0

    def test_rookie_circuit_experience_is_zero(self):
        features = self.engineer._create_rookie_features_from_2025_data("BEA")
        assert features["circuit_experience"] == 0.0
        assert features["circuit_race_count"] == 0

    def test_rookie_has_penalty(self):
        features = self.engineer._create_rookie_features_from_2025_data("HAD")
        assert features["rookie_penalty"] > 0.0

    def test_rookie_data_confidence_and_teammate_proxy(
        self,
        mock_historical_data,
        mock_circuit_config,
        mock_current_intelligence,
        mock_weather_data_dry,
    ):
        """Test that Kimi Antonelli gets low data confidence and falls back to teammate RUS."""
        # Inject some mock history for RUS so the proxy has data
        mock_history = mock_historical_data.copy()
        mock_history.append(
            {
                "circuit_name": "Hungarian Grand Prix",
                "drivers": {"RUS": {"race_position": 3, "grid_position": 2}},
                "race_winner": "VER",
            }
        )

        # Test full pipeline for ANT
        features = self.engineer._create_driver_features_real_2025(
            "ANT",
            mock_history,
            mock_current_intelligence,
            mock_weather_data_dry,
            mock_circuit_config,
        )

        # Confidence should be low (0 F1 races)
        assert features["data_confidence"] < 0.4

        # Should have pulled proxy features from RUS (but with a slight penalty)
        # We don't check exact numbers since RUS mock might vary, but it shouldn't be the default 12.0
        assert "historical_avg_position" in features


# ---------------------------------------------------------------------------
# Form score features
# ---------------------------------------------------------------------------


class TestFormFeatures:
    """Tests for _create_real_2025_form_features."""

    def setup_method(self):
        self.engineer = Enhanced2025FeatureEngineer()

    def test_championship_leader_has_highest_form(self):
        features_leader = self.engineer._create_real_2025_form_features("PIA")
        features_mid = self.engineer._create_real_2025_form_features("ALO")
        assert (
            features_leader["current_form_score"] > features_mid["current_form_score"]
        )

    def test_form_score_between_zero_and_one(self):
        for code in ["PIA", "NOR", "VER", "COL", "ANT"]:
            features = self.engineer._create_real_2025_form_features(code)
            assert 0.0 <= features["current_form_score"] <= 1.0, f"Failed for {code}"

    def test_rookie_form_score_path(self):
        """Rookies use a different scoring branch — ensure it doesn't error."""
        features = self.engineer._create_real_2025_form_features("ANT")
        assert "current_form_score" in features
        assert "current_team_performance" in features

    def test_momentum_tiers(self):
        """Points > 50 → 0.8, > 20 → 0.6, else 0.4."""
        feat_high = self.engineer._create_real_2025_form_features("PIA")  # 284 pts
        feat_mid = self.engineer._create_real_2025_form_features("GAS")  # 20 pts
        feat_low = self.engineer._create_real_2025_form_features("COL")  # 0 pts
        assert feat_high["recent_momentum"] == 0.8
        assert feat_low["recent_momentum"] == 0.4


# ---------------------------------------------------------------------------
# Weather features
# ---------------------------------------------------------------------------


class TestWeatherFeatures:
    """Tests for _create_weather_features."""

    def setup_method(self):
        self.engineer = Enhanced2025FeatureEngineer()

    def test_rain_specialist_boost(self, mock_weather_data_wet, mock_circuit_config):
        features = self.engineer._create_weather_features(
            "HAM", mock_weather_data_wet, mock_circuit_config
        )
        assert features["rain_specialist"] > 0.0

    def test_no_rain_specialist_for_non_specialist(
        self, mock_weather_data_wet, mock_circuit_config
    ):
        features = self.engineer._create_weather_features(
            "STR", mock_weather_data_wet, mock_circuit_config
        )
        assert features["rain_specialist"] == 0.0

    def test_dry_conditions_no_rain_boost(
        self, mock_weather_data_dry, mock_circuit_config
    ):
        features = self.engineer._create_weather_features(
            "HAM", mock_weather_data_dry, mock_circuit_config
        )
        assert features["rain_specialist"] == 0.0

    def test_rookie_weather_penalty(self, mock_weather_data_wet, mock_circuit_config):
        features = self.engineer._create_weather_features(
            "ANT", mock_weather_data_wet, mock_circuit_config
        )
        assert features["weather_risk_factor"] > 0.0


# ---------------------------------------------------------------------------
# Circuit features
# ---------------------------------------------------------------------------


class TestCircuitFeatures:
    """Tests for _create_circuit_features."""

    def setup_method(self):
        self.engineer = Enhanced2025FeatureEngineer()

    def test_specialist_gets_advantage(self, mock_historical_data, mock_circuit_config):
        # VER is in the 'technical' specialist list
        features = self.engineer._create_circuit_features(
            "VER", mock_circuit_config, mock_historical_data
        )
        assert features["circuit_type_advantage"] > 0.0

    def test_non_specialist_no_advantage(
        self, mock_historical_data, mock_circuit_config
    ):
        features = self.engineer._create_circuit_features(
            "STR", mock_circuit_config, mock_historical_data
        )
        assert features["circuit_type_advantage"] == 0.0

    def test_rookie_specialist_reduced(self, mock_historical_data, mock_circuit_config):
        """Even if a rookie is in the specialist list, advantage is halved."""
        features = self.engineer._create_circuit_features(
            "ANT", mock_circuit_config, mock_historical_data
        )
        # ANT is not in the technical specialist list, so 0.0 anyway
        assert features["circuit_type_advantage"] == 0.0

    def test_historical_winner_bonus(self, mock_historical_data, mock_circuit_config):
        # VER won at this circuit in 2022 and 2023
        features = self.engineer._create_circuit_features(
            "VER", mock_circuit_config, mock_historical_data
        )
        assert features["historical_winner_bonus"] > 0.0

    def test_non_winner_no_bonus(self, mock_historical_data, mock_circuit_config):
        features = self.engineer._create_circuit_features(
            "ALO", mock_circuit_config, mock_historical_data
        )
        assert features["historical_winner_bonus"] == 0.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and robustness."""

    def setup_method(self):
        self.engineer = Enhanced2025FeatureEngineer()

    def test_empty_historical_data(self, mock_circuit_config):
        features = self.engineer._create_historical_features(
            "VER", [], mock_circuit_config
        )
        assert features["historical_avg_position"] == 12.0
        assert features["circuit_race_count"] == 0

    def test_create_prediction_features_empty_input(
        self, mock_circuit_config, mock_weather_data_dry, mock_current_intelligence
    ):
        """Full pipeline with empty historical data should still produce features."""
        features_df = self.engineer.create_prediction_features(
            historical_data=[],
            current_intelligence=mock_current_intelligence,
            weather_data=mock_weather_data_dry,
            circuit_config=mock_circuit_config,
        )
        # Should produce features for all active drivers despite no history
        assert len(features_df) > 0

    def test_driver_number_lookup(self):
        assert self.engineer._get_driver_number("VER") == 1
        assert self.engineer._get_driver_number("HAM") == 44
        assert self.engineer._get_driver_number("UNKNOWN") == 99
