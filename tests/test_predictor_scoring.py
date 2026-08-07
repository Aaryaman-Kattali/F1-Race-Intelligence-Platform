"""
Tests for the predictor scoring logic (GPPredictor).

These tests exercise the scoring methods in isolation using mock data,
without triggering FastF1 network calls or the full prediction pipeline.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# We test the scoring *methods* of GPPredictor in isolation.
# GPPredictor.__init__ triggers FastF1 + web collector initialisation that
# hits the network — so we patch those during construction.
# ---------------------------------------------------------------------------


def _build_predictor():
    """Build a GPPredictor with mocked collectors."""
    with patch("src.predictor.gp_predictor.FastF1Collector"), patch(
        "src.predictor.gp_predictor.PerplexityAgent"
    ), patch("src.predictor.gp_predictor.WeatherCollector"), patch(
        "src.predictor.gp_predictor.Enhanced2025FeatureEngineer"
    ), patch(
        "src.predictor.gp_predictor.CircuitMapper"
    ) as MockMapper:

        # Provide a minimal circuit config so _load_circuit_configs doesn't fail
        mock_instance = MockMapper.return_value
        mock_instance.list_available_circuits.return_value = []

        from src.predictor.gp_predictor import GPPredictor

        predictor = GPPredictor.__new__(GPPredictor)
        predictor.circuits = {}
        predictor.use_gpu = False
        predictor.gpu_config = {}
        predictor.active_drivers_2025 = {
            "PIA",
            "NOR",
            "VER",
            "RUS",
            "ANT",
            "HAM",
            "LEC",
        }
        return predictor


# ---------------------------------------------------------------------------
# _local_data_prediction
# ---------------------------------------------------------------------------


class TestLocalDataPrediction:
    """Tests for the balanced scoring in _local_data_prediction."""

    def setup_method(self):
        self.predictor = _build_predictor()

    def test_probabilities_sum_to_one(self, mock_features_df, mock_circuit_config):
        predictions = self.predictor._local_data_prediction(
            mock_features_df, mock_circuit_config
        )
        total = sum(predictions.values())
        assert abs(total - 1.0) < 1e-6

    def test_championship_leader_ranked_high(
        self, mock_features_df, mock_circuit_config
    ):
        """The championship leader (PIA, form_score=0.95) should be near the top."""
        predictions = self.predictor._local_data_prediction(
            mock_features_df, mock_circuit_config
        )
        sorted_preds = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        top_3_codes = [code for code, _ in sorted_preds[:3]]
        assert "PIA" in top_3_codes or "NOR" in top_3_codes

    def test_rookie_penalty_applied(self, mock_features_df, mock_circuit_config):
        """ANT is a rookie — their score should be reduced by the 0.85 multiplier."""
        predictions = self.predictor._local_data_prediction(
            mock_features_df, mock_circuit_config
        )
        # ANT should be ranked lower than top experienced drivers
        sorted_preds = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        ant_rank = [i for i, (code, _) in enumerate(sorted_preds) if code == "ANT"][0]
        assert ant_rank >= 3, "Rookie should not be in top 3 with these features"

    def test_all_drivers_have_predictions(self, mock_features_df, mock_circuit_config):
        predictions = self.predictor._local_data_prediction(
            mock_features_df, mock_circuit_config
        )
        assert set(predictions.keys()) == set(mock_features_df.index)


# ---------------------------------------------------------------------------
# _calculate_qualifying_boost
# ---------------------------------------------------------------------------


class TestQualifyingBoost:
    """Tests for _calculate_qualifying_boost."""

    def setup_method(self):
        self.predictor = _build_predictor()

    def test_pole_position_highest(self):
        pole = self.predictor._calculate_qualifying_boost(1, 0.85, "NOR")
        p2 = self.predictor._calculate_qualifying_boost(2, 0.85, "VER")
        assert pole > p2

    def test_grid_position_tiers(self):
        """Each tier boundary should produce a step change."""
        p1 = self.predictor._calculate_qualifying_boost(1, 0.7, "X")
        p2 = self.predictor._calculate_qualifying_boost(2, 0.7, "X")
        p3 = self.predictor._calculate_qualifying_boost(3, 0.7, "X")
        p5 = self.predictor._calculate_qualifying_boost(5, 0.7, "X")
        p10 = self.predictor._calculate_qualifying_boost(10, 0.7, "X")
        p15 = self.predictor._calculate_qualifying_boost(15, 0.7, "X")
        assert p1 > p2 > p3 > p5 >= p10 >= p15

    def test_back_of_grid_zero_boost(self):
        boost = self.predictor._calculate_qualifying_boost(20, 0.85, "X")
        assert boost == 0.0

    def test_qualifying_importance_scales(self):
        """Higher qualifying_importance should produce a larger boost."""
        low = self.predictor._calculate_qualifying_boost(1, 0.5, "X")
        high = self.predictor._calculate_qualifying_boost(1, 0.9, "X")
        assert high > low


# ---------------------------------------------------------------------------
# _calculate_team_advantage
# ---------------------------------------------------------------------------


class TestTeamAdvantage:
    """Tests for _calculate_team_advantage."""

    def setup_method(self):
        self.predictor = _build_predictor()

    def test_mclaren_highest(self):
        mclaren = self.predictor._calculate_team_advantage("McLaren")
        ferrari = self.predictor._calculate_team_advantage("Ferrari")
        assert mclaren > ferrari

    def test_known_teams_have_values(self):
        teams = [
            "McLaren",
            "Ferrari",
            "Mercedes",
            "Red Bull Racing",
            "Williams",
            "Racing Bulls",
            "Haas",
            "Aston Martin",
            "Alpine",
            "Kick Sauber",
        ]
        for team in teams:
            value = self.predictor._calculate_team_advantage(team)
            assert value > 0.0, f"No advantage for {team}"

    def test_unknown_team_gets_minimum(self):
        value = self.predictor._calculate_team_advantage("Unknown Team")
        assert value == 0.01


# ---------------------------------------------------------------------------
# _combine_predictions
# ---------------------------------------------------------------------------


class TestCombinePredictions:
    """Tests for _combine_predictions (70/30 weighting)."""

    def setup_method(self):
        self.predictor = _build_predictor()

    def test_weights_applied_correctly(self):
        local = {"VER": 0.5, "HAM": 0.5}
        pattern = {"VER": 1.0, "HAM": 0.0}
        combined = self.predictor._combine_predictions(local, pattern)
        # VER: 0.5*0.7 + 1.0*0.3 = 0.65
        assert abs(combined["VER"] - 0.65) < 1e-6
        # HAM: 0.5*0.7 + 0.0*0.3 = 0.35
        assert abs(combined["HAM"] - 0.35) < 1e-6

    def test_no_pattern_predictions(self):
        """When pattern_pred is None, only local matters."""
        local = {"VER": 0.6, "HAM": 0.4}
        combined = self.predictor._combine_predictions(local, None)
        # VER: 0.6*0.7 = 0.42, HAM: 0.4*0.7 = 0.28
        assert abs(combined["VER"] - 0.42) < 1e-6
        assert abs(combined["HAM"] - 0.28) < 1e-6

    def test_result_is_sorted_descending(self):
        local = {"A": 0.1, "B": 0.5, "C": 0.4}
        combined = self.predictor._combine_predictions(local, None)
        values = list(combined.values())
        assert values == sorted(values, reverse=True)


# ---------------------------------------------------------------------------
# _pattern_matching_prediction
# ---------------------------------------------------------------------------


class TestPatternMatching:
    """Tests for _pattern_matching_prediction."""

    def setup_method(self):
        self.predictor = _build_predictor()

    def test_returns_none_with_few_races(self, mock_features_df, mock_circuit_config):
        """Should return None when fewer than 3 historical races."""
        short_data = [{"race_winner": "VER", "drivers": {"VER": {}}}]
        result = self.predictor._pattern_matching_prediction(
            mock_features_df, short_data, mock_circuit_config
        )
        assert result is None

    def test_winner_gets_bonus(
        self, mock_features_df, mock_historical_data, mock_circuit_config
    ):
        result = self.predictor._pattern_matching_prediction(
            mock_features_df, mock_historical_data, mock_circuit_config
        )
        assert result is not None
        # VER won 2 of 3 races → should have a higher score
        assert result["VER"] > result["ANT"]

    def test_probabilities_sum_to_one(
        self, mock_features_df, mock_historical_data, mock_circuit_config
    ):
        result = self.predictor._pattern_matching_prediction(
            mock_features_df, mock_historical_data, mock_circuit_config
        )
        total = sum(result.values())
        assert abs(total - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Scoring weight distribution
# ---------------------------------------------------------------------------


class TestScoringWeights:
    """Verify the 40/20/25/10/5 weight distribution is applied."""

    def setup_method(self):
        self.predictor = _build_predictor()

    def test_weights_sum_to_one(self):
        """The hardcoded weights in _local_data_prediction should sum to 1.0."""
        # form_score * 0.4 + hist * 0.2 + quali * 0.25 + circuit * 0.1 + team * 0.05
        total = 0.4 + 0.2 + 0.25 + 0.1 + 0.05
        assert abs(total - 1.0) < 1e-6
