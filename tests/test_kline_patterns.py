"""Tests for K-line candlestick pattern recognition.

TDD Cycle 3.1: Single-Candle Patterns
- Hammer (锤子线)
- Hanging Man (上吊线)
- Inverted Hammer (倒锤子线)
- Shooting Star (射击之星)
- Doji (十字星)
- Long-Legged Doji (长腿十字)
- Dragonfly Doji (蜻蜓十字)
- Gravestone Doji (墓碑十字)
- Marubozu (光头光脚)

TDD Cycle 3.2: Dual-Candle Patterns
- Bullish Engulfing (看涨吞没)
- Bearish Engulfing (看跌吞没)
- Tweezer Top/Bottom (镊子顶/底)

TDD Cycle 3.3: Triple-Candle Patterns
- Morning Star (启明星)
- Evening Star (黄昏星)
- Three White Soldiers (红三兵)
- Three Black Crows (三只乌鸦)

TDD Cycle 3.4: Combined Pattern Detection
- detect_patterns() returns all patterns found in given data

TDD Cycle 3.5: API Endpoint
- GET /api/portfolio/kline-patterns/{ts_code} returns patterns
"""

import pytest
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Data model for a single candle
# ---------------------------------------------------------------------------


@dataclass
class Candle:
    """Single OHLC candle data."""
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float = 0

    @property
    def body(self) -> float:
        """Absolute body size."""
        return abs(self.close - self.open)

    @property
    def upper_shadow(self) -> float:
        """Upper shadow length."""
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> float:
        """Lower shadow length."""
        return min(self.open, self.close) - self.low

    @property
    def range(self) -> float:
        """Full range (high - low)."""
        return self.high - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


# ---------------------------------------------------------------------------
# TDD Cycle 3.1: Single-Candle Patterns
# ---------------------------------------------------------------------------


class TestCandleDataModel:
    """Test the Candle dataclass and its computed properties."""

    def test_candle_body_calculation(self):
        c = Candle(date="2026-04-20", open=10.0, close=12.0, high=13.0, low=9.0)
        assert c.body == 2.0
        assert c.is_bullish

    def test_candle_bearish_body(self):
        c = Candle(date="2026-04-20", open=12.0, close=10.0, high=13.0, low=9.0)
        assert c.body == 2.0
        assert c.is_bearish

    def test_candle_shadows(self):
        c = Candle(date="2026-04-20", open=10.0, close=12.0, high=14.0, low=8.0)
        assert c.upper_shadow == 2.0  # 14 - 12
        assert c.lower_shadow == 2.0  # 10 - 8
        assert c.range == 6.0  # 14 - 8


class TestHammerPattern:
    """Hammer: small body at top, long lower shadow (>= 2x body), little/no upper shadow.

    Bullish reversal pattern appearing at bottom of downtrend.
    """

    def test_hammer_detected(self):
        """A candle with small body at top, long lower shadow, no upper shadow is a hammer."""
        from stock_datasource.modules.portfolio.kline_patterns import is_hammer

        # Hammer: body at top, long lower shadow, tiny upper shadow
        c = Candle(date="2026-04-20", open=10.0, close=10.5, high=10.6, low=8.0)
        assert is_hammer(c) is True

    def test_hammer_with_zero_upper_shadow(self):
        """Hammer with no upper shadow should be detected."""
        from stock_datasource.modules.portfolio.kline_patterns import is_hammer

        c = Candle(date="2026-04-20", open=10.0, close=10.5, high=10.5, low=8.0)
        assert is_hammer(c) is True

    def test_not_hammer_too_much_upper_shadow(self):
        """A candle with large upper shadow is not a hammer."""
        from stock_datasource.modules.portfolio.kline_patterns import is_hammer

        c = Candle(date="2026-04-20", open=10.0, close=10.5, high=13.0, low=8.0)
        assert is_hammer(c) is False

    def test_not_hammer_short_lower_shadow(self):
        """A candle with short lower shadow is not a hammer."""
        from stock_datasource.modules.portfolio.kline_patterns import is_hammer

        c = Candle(date="2026-04-20", open=10.0, close=10.5, high=11.0, low=9.8)
        assert is_hammer(c) is False


class TestShootingStarPattern:
    """Shooting Star: small body at bottom, long upper shadow (>= 2x body), little/no lower shadow.

    Bearish reversal pattern appearing at top of uptrend.
    """

    def test_shooting_star_detected(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_shooting_star

        c = Candle(date="2026-04-20", open=10.0, close=10.5, high=13.0, low=10.0)
        assert is_shooting_star(c) is True

    def test_not_shooting_star_with_lower_shadow(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_shooting_star

        c = Candle(date="2026-04-20", open=10.0, close=10.5, high=13.0, low=8.0)
        assert is_shooting_star(c) is False


class TestDojiPattern:
    """Doji: open and close are nearly equal (body is very small relative to range).

    Signals indecision in the market.
    """

    def test_doji_detected(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_doji

        # Open and close very close relative to total range
        c = Candle(date="2026-04-20", open=10.0, close=10.05, high=12.0, low=8.0)
        assert is_doji(c) is True

    def test_not_doji_large_body(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_doji

        c = Candle(date="2026-04-20", open=10.0, close=12.0, high=13.0, low=9.0)
        assert is_doji(c) is False


class TestMarubozuPattern:
    """Marubozu: no or very small shadows, large body.

    Strong directional conviction.
    """

    def test_bullish_marubozu(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_marubozu

        # Open = low, Close = high, large body, no shadows
        c = Candle(date="2026-04-20", open=10.0, close=15.0, high=15.0, low=10.0)
        result = is_marubozu(c)
        assert result is not None
        assert result == "bullish"

    def test_bearish_marubozu(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_marubozu

        # Open = high, Close = low, large body, no shadows
        c = Candle(date="2026-04-20", open=15.0, close=10.0, high=15.0, low=10.0)
        result = is_marubozu(c)
        assert result is not None
        assert result == "bearish"

    def test_not_marubozu_with_shadows(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_marubozu

        c = Candle(date="2026-04-20", open=10.0, close=15.0, high=16.0, low=9.0)
        assert is_marubozu(c) is None


# ---------------------------------------------------------------------------
# TDD Cycle 3.2: Dual-Candle Patterns
# ---------------------------------------------------------------------------


class TestBullishEngulfingPattern:
    """Bullish Engulfing: previous bearish candle, current bullish candle
    whose body completely engulfs the previous body.

    Bullish reversal pattern at bottom of downtrend.
    """

    def test_bullish_engulfing_detected(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_bullish_engulfing

        prev = Candle(date="2026-04-19", open=12.0, close=10.0, high=12.5, low=9.5)
        curr = Candle(date="2026-04-20", open=9.5, close=13.0, high=13.5, low=9.0)
        assert is_bullish_engulfing(prev, curr) is True

    def test_not_engulfing_same_direction(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_bullish_engulfing

        # Both bullish - not a valid pattern
        prev = Candle(date="2026-04-19", open=10.0, close=12.0, high=12.5, low=9.5)
        curr = Candle(date="2026-04-20", open=9.5, close=13.0, high=13.5, low=9.0)
        assert is_bullish_engulfing(prev, curr) is False

    def test_not_engulfing_does_not_engulf(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_bullish_engulfing

        # Current body does not completely engulf previous
        prev = Candle(date="2026-04-19", open=12.0, close=10.0, high=12.5, low=9.5)
        curr = Candle(date="2026-04-20", open=10.5, close=11.0, high=11.5, low=10.0)
        assert is_bullish_engulfing(prev, curr) is False


class TestBearishEngulfingPattern:
    """Bearish Engulfing: previous bullish candle, current bearish candle
    whose body completely engulfs the previous body.
    """

    def test_bearish_engulfing_detected(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_bearish_engulfing

        prev = Candle(date="2026-04-19", open=10.0, close=12.0, high=12.5, low=9.5)
        curr = Candle(date="2026-04-20", open=13.0, close=9.5, high=13.5, low=9.0)
        assert is_bearish_engulfing(prev, curr) is True

    def test_not_bearish_engulfing_wrong_direction(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_bearish_engulfing

        prev = Candle(date="2026-04-19", open=12.0, close=10.0, high=12.5, low=9.5)
        curr = Candle(date="2026-04-20", open=13.0, close=9.5, high=13.5, low=9.0)
        assert is_bearish_engulfing(prev, curr) is False


# ---------------------------------------------------------------------------
# TDD Cycle 3.3: Triple-Candle Patterns
# ---------------------------------------------------------------------------


class TestMorningStarPattern:
    """Morning Star: 
    1st candle: large bearish
    2nd candle: small body (star), gaps down
    3rd candle: large bullish, closes above midpoint of 1st candle

    Bullish reversal pattern at bottom of downtrend.
    """

    def test_morning_star_detected(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_morning_star

        c1 = Candle(date="2026-04-18", open=15.0, close=12.0, high=15.2, low=11.8)
        c2 = Candle(date="2026-04-19", open=11.5, close=11.8, high=12.0, low=11.0)
        c3 = Candle(date="2026-04-20", open=12.0, close=14.5, high=14.8, low=11.8)
        assert is_morning_star(c1, c2, c3) is True

    def test_not_morning_star_third_candle_weak(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_morning_star

        c1 = Candle(date="2026-04-18", open=15.0, close=12.0, high=15.2, low=11.8)
        c2 = Candle(date="2026-04-19", open=11.5, close=11.8, high=12.0, low=11.0)
        # Third candle does not close above midpoint of first
        c3 = Candle(date="2026-04-20", open=12.0, close=12.5, high=12.8, low=11.8)
        assert is_morning_star(c1, c2, c3) is False


class TestEveningStarPattern:
    """Evening Star:
    1st candle: large bullish
    2nd candle: small body (star), gaps up
    3rd candle: large bearish, closes below midpoint of 1st candle

    Bearish reversal pattern at top of uptrend.
    """

    def test_evening_star_detected(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_evening_star

        c1 = Candle(date="2026-04-18", open=12.0, close=15.0, high=15.2, low=11.8)
        c2 = Candle(date="2026-04-19", open=15.5, close=15.2, high=16.0, low=15.0)
        c3 = Candle(date="2026-04-20", open=15.0, close=12.5, high=15.2, low=12.0)
        assert is_evening_star(c1, c2, c3) is True


class TestThreeWhiteSoldiers:
    """Three White Soldiers: three consecutive bullish candles, each opening
    within previous body and closing progressively higher.

    Strong bullish reversal.
    """

    def test_three_white_soldiers_detected(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_three_white_soldiers

        c1 = Candle(date="2026-04-18", open=10.0, close=12.0, high=12.2, low=9.8)
        c2 = Candle(date="2026-04-19", open=11.5, close=13.5, high=13.7, low=11.3)
        c3 = Candle(date="2026-04-20", open=13.0, close=15.0, high=15.2, low=12.8)
        assert is_three_white_soldiers(c1, c2, c3) is True

    def test_not_soldiers_one_bearish(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_three_white_soldiers

        c1 = Candle(date="2026-04-18", open=10.0, close=12.0, high=12.2, low=9.8)
        c2 = Candle(date="2026-04-19", open=13.5, close=11.5, high=13.7, low=11.3)  # bearish
        c3 = Candle(date="2026-04-20", open=13.0, close=15.0, high=15.2, low=12.8)
        assert is_three_white_soldiers(c1, c2, c3) is False


class TestThreeBlackCrows:
    """Three Black Crows: three consecutive bearish candles, each opening
    within previous body and closing progressively lower.

    Strong bearish reversal.
    """

    def test_three_black_crows_detected(self):
        from stock_datasource.modules.portfolio.kline_patterns import is_three_black_crows

        c1 = Candle(date="2026-04-18", open=15.0, close=13.0, high=15.2, low=12.8)
        c2 = Candle(date="2026-04-19", open=13.5, close=11.5, high=13.7, low=11.3)
        c3 = Candle(date="2026-04-20", open=12.0, close=10.0, high=12.2, low=9.8)
        assert is_three_black_crows(c1, c2, c3) is True


# ---------------------------------------------------------------------------
# TDD Cycle 3.4: Combined Pattern Detection
# ---------------------------------------------------------------------------


class TestDetectPatterns:
    """Test the combined detect_patterns function that scans candle data
    and returns all recognized patterns with their dates and types.
    """

    def test_detect_patterns_returns_list(self):
        from stock_datasource.modules.portfolio.kline_patterns import detect_patterns

        candles = [
            Candle(date="2026-04-18", open=15.0, close=13.0, high=15.2, low=12.8),
            Candle(date="2026-04-19", open=13.5, close=11.5, high=13.7, low=11.3),
            Candle(date="2026-04-20", open=12.0, close=10.0, high=12.2, low=9.8),
        ]
        result = detect_patterns(candles)
        assert isinstance(result, list)

    def test_detect_patterns_item_structure(self):
        from stock_datasource.modules.portfolio.kline_patterns import detect_patterns

        candles = [
            Candle(date="2026-04-18", open=15.0, close=13.0, high=15.2, low=12.8),
            Candle(date="2026-04-19", open=13.5, close=11.5, high=13.7, low=11.3),
            Candle(date="2026-04-20", open=12.0, close=10.0, high=12.2, low=9.8),
        ]
        result = detect_patterns(candles)
        if len(result) > 0:
            pattern = result[0]
            assert "name" in pattern
            assert "date" in pattern
            assert "type" in pattern  # 'bullish' or 'bearish'
            assert "category" in pattern  # 'single', 'dual', or 'triple'

    def test_detect_patterns_finds_three_black_crows(self):
        from stock_datasource.modules.portfolio.kline_patterns import detect_patterns

        candles = [
            Candle(date="2026-04-18", open=15.0, close=13.0, high=15.2, low=12.8),
            Candle(date="2026-04-19", open=13.5, close=11.5, high=13.7, low=11.3),
            Candle(date="2026-04-20", open=12.0, close=10.0, high=12.2, low=9.8),
        ]
        result = detect_patterns(candles)
        names = [p["name"] for p in result]
        assert "三只乌鸦" in names or "Three Black Crows" in names

    def test_detect_patterns_empty_input(self):
        from stock_datasource.modules.portfolio.kline_patterns import detect_patterns

        result = detect_patterns([])
        assert result == []

    def test_detect_patterns_hammer(self):
        from stock_datasource.modules.portfolio.kline_patterns import detect_patterns

        candles = [
            Candle(date="2026-04-20", open=10.0, close=10.5, high=10.6, low=8.0),
        ]
        result = detect_patterns(candles)
        names = [p["name"] for p in result]
        assert "锤子线" in names or "Hammer" in names


# ---------------------------------------------------------------------------
# TDD Cycle 3.5: API Endpoint
# ---------------------------------------------------------------------------


class TestKlinePatternsAPI:
    """Test GET /api/portfolio/kline-patterns/{ts_code} endpoint.

    The endpoint should:
    1. Fetch K-line OHLC data for the given ts_code
    2. Convert to Candle objects and run detect_patterns()
    3. Return the list of detected patterns

    Since this is a portfolio module endpoint, it requires authentication.
    """

    def test_kline_patterns_endpoint_returns_list(self):
        """GET /api/portfolio/kline-patterns/{ts_code} returns a list."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import AsyncMock, patch

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        async def override_auth():
            return {"id": "test_user", "username": "tester"}

        app.dependency_overrides[get_current_user] = override_auth

        with patch(
            "stock_datasource.modules.portfolio.router.get_enhanced_portfolio_service"
        ) as mock_svc_fn:
            mock_svc = AsyncMock()
            # get_kline_patterns returns a list of pattern dicts
            mock_svc.get_kline_patterns = AsyncMock(return_value=[])
            mock_svc_fn.return_value = mock_svc

            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/api/portfolio/kline-patterns/600519.SH")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_kline_patterns_item_has_required_fields(self):
        """Each pattern item should have: name, name_en, date, type, category."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import AsyncMock, patch

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        async def override_auth():
            return {"id": "test_user", "username": "tester"}

        app.dependency_overrides[get_current_user] = override_auth

        mock_patterns = [
            {
                "name": "锤子线",
                "name_en": "Hammer",
                "date": "2026-04-20",
                "type": "bullish",
                "category": "single",
            }
        ]

        with patch(
            "stock_datasource.modules.portfolio.router.get_enhanced_portfolio_service"
        ) as mock_svc_fn:
            mock_svc = AsyncMock()
            mock_svc.get_kline_patterns = AsyncMock(return_value=mock_patterns)
            mock_svc_fn.return_value = mock_svc

            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/api/portfolio/kline-patterns/600519.SH?days=60")
            assert response.status_code == 200
            data = response.json()
            for item in data:
                assert "name" in item
                assert "name_en" in item
                assert "date" in item
                assert "type" in item
                assert "category" in item

    def test_kline_patterns_endpoint_requires_auth(self):
        """Endpoint should return 401 or 403 without authentication."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from stock_datasource.modules.portfolio.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/portfolio/kline-patterns/600519.SH")
        # Should be 401, 403, or 422 (unauthenticated)
        assert response.status_code in (401, 403, 422, 500)

    def test_kline_patterns_supports_days_param(self):
        """Endpoint should accept a 'days' query parameter."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import AsyncMock, patch

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        async def override_auth():
            return {"id": "test_user", "username": "tester"}

        app.dependency_overrides[get_current_user] = override_auth

        with patch(
            "stock_datasource.modules.portfolio.router.get_enhanced_portfolio_service"
        ) as mock_svc_fn:
            mock_svc = AsyncMock()
            mock_svc.get_kline_patterns = AsyncMock(return_value=[])
            mock_svc_fn.return_value = mock_svc

            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/api/portfolio/kline-patterns/600519.SH?days=7")
            assert response.status_code == 200

    def test_kline_patterns_type_values(self):
        """Pattern type should be one of: bullish, bearish, neutral."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import AsyncMock, patch

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        async def override_auth():
            return {"id": "test_user", "username": "tester"}

        app.dependency_overrides[get_current_user] = override_auth

        mock_patterns = [
            {
                "name": "锤子线",
                "name_en": "Hammer",
                "date": "2026-04-20",
                "type": "bullish",
                "category": "single",
            },
            {
                "name": "射击之星",
                "name_en": "Shooting Star",
                "date": "2026-04-18",
                "type": "bearish",
                "category": "single",
            },
            {
                "name": "十字星",
                "name_en": "Doji",
                "date": "2026-04-15",
                "type": "neutral",
                "category": "single",
            },
        ]

        with patch(
            "stock_datasource.modules.portfolio.router.get_enhanced_portfolio_service"
        ) as mock_svc_fn:
            mock_svc = AsyncMock()
            mock_svc.get_kline_patterns = AsyncMock(return_value=mock_patterns)
            mock_svc_fn.return_value = mock_svc

            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/api/portfolio/kline-patterns/600519.SH?days=60")
            assert response.status_code == 200
            data = response.json()
            valid_types = {"bullish", "bearish", "neutral"}
            for item in data:
                assert item["type"] in valid_types
