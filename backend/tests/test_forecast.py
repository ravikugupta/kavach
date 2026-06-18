"""
Unit tests for app.services.forecast — linear trend and hotspot risk scoring.
Run with:  cd backend && source venv/bin/activate && python -m pytest tests/ -v
"""
import pytest
from app.services.forecast import _linear_trend, forecast_crime_trends, forecast_hotspot_risk


# ---------------------------------------------------------------------------
# _linear_trend (pure maths — no DB required)
# ---------------------------------------------------------------------------

class TestLinearTrend:
    def test_flat_series_slope_is_zero(self):
        slope, intercept = _linear_trend([5, 5, 5, 5])
        assert abs(slope) < 1e-9

    def test_strictly_rising_series_positive_slope(self):
        slope, _ = _linear_trend([1, 2, 3, 4, 5])
        assert slope > 0

    def test_strictly_falling_series_negative_slope(self):
        slope, _ = _linear_trend([5, 4, 3, 2, 1])
        assert slope < 0

    def test_single_value_returns_zero_slope(self):
        slope, intercept = _linear_trend([7])
        assert slope == 0.0
        assert intercept == 7.0

    def test_empty_returns_zero(self):
        slope, intercept = _linear_trend([])
        assert slope == 0.0
        assert intercept == 0.0

    def test_known_values(self):
        # y = x => slope should be ~1
        slope, intercept = _linear_trend([0, 1, 2, 3, 4])
        assert abs(slope - 1.0) < 1e-9
        assert abs(intercept) < 1e-9

    def test_intercept_consistency(self):
        values = [3, 5, 7, 9]
        slope, intercept = _linear_trend(values)
        # Reconstruct first point: intercept + slope * 0
        predicted_first = intercept + slope * 0
        assert abs(predicted_first - 3.0) < 0.5  # reasonable fit


# ---------------------------------------------------------------------------
# forecast_crime_trends (requires DB)
# ---------------------------------------------------------------------------

class TestForecastCrimeTrends:
    def test_returns_expected_keys(self):
        result = forecast_crime_trends()
        assert "forecasts"               in result
        assert "top_rising_crime_types"  in result
        assert "evidence"                in result
        assert "months_modelled"         in result

    def test_forecasts_are_list_of_dicts(self):
        result = forecast_crime_trends()
        assert isinstance(result["forecasts"], list)
        for f in result["forecasts"]:
            assert "crime_type"            in f
            assert "trend"                 in f
            assert "predicted_next_month"  in f
            assert "trend_slope"           in f
            assert "historical_monthly"    in f

    def test_predicted_next_month_is_non_negative(self):
        result = forecast_crime_trends()
        for f in result["forecasts"]:
            assert f["predicted_next_month"] >= 0

    def test_trend_values_are_valid(self):
        result = forecast_crime_trends()
        valid_trends = {"rising", "stable", "declining"}
        for f in result["forecasts"]:
            assert f["trend"] in valid_trends, f"Unexpected trend: {f['trend']}"

    def test_city_filter_reduces_results(self):
        all_result  = forecast_crime_trends()
        city_result = forecast_crime_trends(city="Bengaluru")
        # Filtering should yield <= total count (or equal if all cases are in that city)
        total_all  = sum(
            sum(f["historical_monthly"].values())
            for f in all_result["forecasts"]
        )
        total_city = sum(
            sum(f["historical_monthly"].values())
            for f in city_result["forecasts"]
        )
        assert total_city <= total_all

    def test_city_filter_reflected_in_evidence(self):
        result = forecast_crime_trends(city="Mysuru")
        assert "Mysuru" in result["evidence"]

    def test_unknown_city_returns_empty_forecasts(self):
        result = forecast_crime_trends(city="NonExistentCity_XYZ")
        assert result["forecasts"] == []

    def test_top_rising_crime_types_is_list(self):
        result = forecast_crime_trends()
        assert isinstance(result["top_rising_crime_types"], list)

    def test_top_rising_all_marked_rising(self):
        result = forecast_crime_trends()
        rising_types = {f["crime_type"] for f in result["forecasts"] if f["trend"] == "rising"}
        for ct in result["top_rising_crime_types"]:
            assert ct in rising_types


# ---------------------------------------------------------------------------
# forecast_hotspot_risk (requires DB)
# ---------------------------------------------------------------------------

class TestForecastHotspotRisk:
    def test_returns_expected_keys(self):
        result = forecast_hotspot_risk()
        assert "hotspot_forecast" in result
        assert "evidence"         in result

    def test_hotspot_count_respects_top_n(self):
        for n in [3, 5, 10]:
            result = forecast_hotspot_risk(top_n=n)
            assert len(result["hotspot_forecast"]) <= n

    def test_each_hotspot_has_required_fields(self):
        result = forecast_hotspot_risk(top_n=5)
        for h in result["hotspot_forecast"]:
            for field in ("area_name", "city", "total_cases", "recent_cases_3m",
                          "risk_score", "risk_level"):
                assert field in h, f"Missing field '{field}' in hotspot entry"

    def test_risk_scores_between_0_and_1(self):
        result = forecast_hotspot_risk(top_n=10)
        for h in result["hotspot_forecast"]:
            assert 0.0 <= h["risk_score"] <= 1.0

    def test_risk_levels_are_valid(self):
        result = forecast_hotspot_risk(top_n=10)
        valid = {"HIGH", "MEDIUM", "LOW"}
        for h in result["hotspot_forecast"]:
            assert h["risk_level"] in valid

    def test_sorted_descending_by_risk_score(self):
        result = forecast_hotspot_risk(top_n=10)
        scores = [h["risk_score"] for h in result["hotspot_forecast"]]
        assert scores == sorted(scores, reverse=True)

    def test_recent_cases_lte_total(self):
        result = forecast_hotspot_risk(top_n=10)
        for h in result["hotspot_forecast"]:
            assert h["recent_cases_3m"] <= h["total_cases"]
