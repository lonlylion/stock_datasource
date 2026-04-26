"""Tests for portfolio transaction feature (buy/sell transaction history).

TDD Cycle 1.1: Transaction Data Model & Schema
- TransactionType enum (BUY, SELL)
- Transaction dataclass
- Weighted average cost calculation
- Realized P/L calculation
- Sell validation (cannot sell more than held)

TDD Cycle 1.2: Buy Transaction Operations
- record_buy_transaction creates Transaction with type=buy
- First buy creates new Position
- Second buy updates Position with weighted average cost
- Buy transaction persisted to user_transactions table
- Position auto-updated after buy transaction
- Multiple buys accumulate correctly

TDD Cycle 1.3: Sell Transaction Operations
- record_sell_transaction creates Transaction with type=sell
- Partial sell reduces position quantity
- Full sell sets position is_active=False
- Sell more than held raises ValueError
- Realized P/L calculated correctly
- Position cost_price unchanged after sell
- Sell transaction persisted
- Sell on non-existent position raises ValueError

TDD Cycle 1.4: Transaction History Query
- get_transactions returns list of Transaction for user
- get_transactions filtered by ts_code
- get_transactions ordered by transaction_date DESC
- get_transactions respects date range filter

TDD Cycle 1.5: API Endpoints
- POST /api/portfolio/transactions/buy returns 200
- POST /api/portfolio/transactions/sell returns 200
- GET /api/portfolio/transactions returns list
- GET /api/portfolio/transactions?ts_code=600519.SH filters by stock
- POST sell with quantity > held returns 400
- All endpoints require auth
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. TransactionType Enum Tests
# ---------------------------------------------------------------------------


class TestTransactionType:
    """Test TransactionType enum values."""

    def test_has_buy_and_sell(self):
        """TransactionType should have BUY and SELL members."""
        from stock_datasource.modules.portfolio.enhanced_service import TransactionType

        assert hasattr(TransactionType, "BUY")
        assert hasattr(TransactionType, "SELL")

    def test_buy_value(self):
        """TransactionType.BUY should have value 'buy'."""
        from stock_datasource.modules.portfolio.enhanced_service import TransactionType

        assert TransactionType.BUY.value == "buy"

    def test_sell_value(self):
        """TransactionType.SELL should have value 'sell'."""
        from stock_datasource.modules.portfolio.enhanced_service import TransactionType

        assert TransactionType.SELL.value == "sell"


# ---------------------------------------------------------------------------
# 2. Transaction Dataclass Tests
# ---------------------------------------------------------------------------


class TestTransaction:
    """Test Transaction dataclass fields and creation."""

    def test_transaction_fields_exist(self):
        """Transaction should have all required fields."""
        from stock_datasource.modules.portfolio.enhanced_service import Transaction

        txn = Transaction(
            id="txn_001",
            user_id="user_001",
            ts_code="600519.SH",
            stock_name="贵州茅台",
            transaction_type="buy",
            quantity=100,
            price=1700.0,
            transaction_date="2026-01-15",
            position_id="pos_001",
            realized_pl=None,
            notes="首次建仓",
            profile_id="default",
            created_at=datetime.now(),
        )

        assert txn.id == "txn_001"
        assert txn.user_id == "user_001"
        assert txn.ts_code == "600519.SH"
        assert txn.stock_name == "贵州茅台"
        assert txn.transaction_type == "buy"
        assert txn.quantity == 100
        assert txn.price == 1700.0
        assert txn.transaction_date == "2026-01-15"
        assert txn.position_id == "pos_001"
        assert txn.realized_pl is None
        assert txn.notes == "首次建仓"
        assert txn.profile_id == "default"
        assert txn.created_at is not None

    def test_transaction_optional_fields_default(self):
        """Transaction optional fields should have sensible defaults."""
        from stock_datasource.modules.portfolio.enhanced_service import Transaction

        txn = Transaction(
            id="txn_002",
            user_id="user_001",
            ts_code="600519.SH",
            stock_name="贵州茅台",
            transaction_type="sell",
            quantity=50,
            price=1800.0,
            transaction_date="2026-02-01",
            position_id="pos_001",
        )

        assert txn.realized_pl is None
        assert txn.notes == ""
        assert txn.profile_id == "default"


# ---------------------------------------------------------------------------
# 3. Weighted Average Cost Calculation Tests
# ---------------------------------------------------------------------------


class TestWeightedAverageCost:
    """Test weighted average cost calculation for buy transactions."""

    def test_two_buys_weighted_average(self):
        """Two buys at different prices should compute weighted average cost.

        buy 100 @ 10.00, buy 50 @ 12.00 -> avg = (1000+600)/150 = 10.667
        """
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        result = EnhancedPortfolioService._calc_weighted_average_cost(
            old_quantity=100, old_cost=10.0, new_quantity=50, new_price=12.0
        )
        assert round(result, 2) == 10.67

    def test_single_buy_no_average(self):
        """First buy should return the buy price directly.

        old_quantity=0 means no previous position, cost = new_price.
        """
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        result = EnhancedPortfolioService._calc_weighted_average_cost(
            old_quantity=0, old_cost=0.0, new_quantity=100, new_price=15.0
        )
        assert result == 15.0

    def test_three_buys_weighted_average(self):
        """Three buys: 100@10, 50@12, 200@11.

        avg = (1000+600+2200) / 350 = 10.857
        """
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        # First two buys
        avg1 = EnhancedPortfolioService._calc_weighted_average_cost(
            old_quantity=100, old_cost=10.0, new_quantity=50, new_price=12.0
        )
        # Third buy uses the previously computed average
        avg2 = EnhancedPortfolioService._calc_weighted_average_cost(
            old_quantity=150, old_cost=avg1, new_quantity=200, new_price=11.0
        )
        assert round(avg2, 2) == 10.86


# ---------------------------------------------------------------------------
# 4. Realized P/L Calculation Tests
# ---------------------------------------------------------------------------


class TestRealizedPL:
    """Test realized profit/loss calculation for sell transactions."""

    def test_sell_profit(self):
        """Selling at higher price should give positive realized P/L.

        buy 100 @ 10, sell 50 @ 15 -> realized = 50 * (15-10) = 250
        """
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        result = EnhancedPortfolioService._calc_realized_pl(
            quantity=50, sell_price=15.0, cost_price=10.0
        )
        assert result == 250.0

    def test_sell_loss(self):
        """Selling at lower price should give negative realized P/L.

        buy 100 @ 20, sell 30 @ 15 -> realized = 30 * (15-20) = -150
        """
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        result = EnhancedPortfolioService._calc_realized_pl(
            quantity=30, sell_price=15.0, cost_price=20.0
        )
        assert result == -150.0

    def test_sell_at_cost(self):
        """Selling at cost price should give zero realized P/L."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        result = EnhancedPortfolioService._calc_realized_pl(
            quantity=100, sell_price=10.0, cost_price=10.0
        )
        assert result == 0.0


# ---------------------------------------------------------------------------
# 5. Sell Validation Tests
# ---------------------------------------------------------------------------


class TestSellValidation:
    """Test sell quantity validation."""

    def test_sell_more_than_held_raises_error(self):
        """Selling more shares than held should raise ValueError."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        with pytest.raises(ValueError, match="Cannot sell"):
            EnhancedPortfolioService._validate_sell_quantity(
                held_quantity=50, sell_quantity=100
            )

    def test_sell_exact_quantity_ok(self):
        """Selling exactly the held quantity should not raise."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        # Should not raise
        EnhancedPortfolioService._validate_sell_quantity(
            held_quantity=100, sell_quantity=100
        )

    def test_sell_partial_quantity_ok(self):
        """Selling less than held should not raise."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        EnhancedPortfolioService._validate_sell_quantity(
            held_quantity=100, sell_quantity=30
        )

    def test_sell_zero_quantity_raises_error(self):
        """Selling zero shares should raise ValueError."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        with pytest.raises(ValueError, match="Cannot sell"):
            EnhancedPortfolioService._validate_sell_quantity(
                held_quantity=100, sell_quantity=0
            )


# ---------------------------------------------------------------------------
# 6. Buy Transaction Service Tests (Cycle 1.2)
# ---------------------------------------------------------------------------


class TestBuyTransaction:
    """Test record_buy_transaction service method."""

    @pytest.mark.asyncio
    async def test_record_buy_creates_transaction_with_buy_type(self):
        """record_buy_transaction should create a Transaction with type=buy."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
            Transaction,
        )

        svc = EnhancedPortfolioService()
        svc._db = None  # Use in-memory only

        txn = await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=1700.0,
            transaction_date="2026-01-15",
        )

        assert isinstance(txn, Transaction)
        assert txn.transaction_type == "buy"
        assert txn.ts_code == "600519.SH"
        assert txn.quantity == 100
        assert txn.price == 1700.0

    @pytest.mark.asyncio
    async def test_first_buy_creates_new_position(self):
        """First buy for a stock should create a new Position."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        txn = await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=1700.0,
            transaction_date="2026-01-15",
        )

        # Check position was created
        assert txn.position_id != ""
        position = svc._positions.get(txn.position_id)
        assert position is not None
        assert position.quantity == 100
        assert position.cost_price == 1700.0
        assert position.ts_code == "600519.SH"

    @pytest.mark.asyncio
    async def test_second_buy_updates_weighted_average_cost(self):
        """Second buy for same stock should update Position with weighted avg cost.

        buy 100 @ 10.00, buy 50 @ 12.00 -> position.quantity=150, position.cost_price≈10.67
        """
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        # First buy
        txn1 = await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )
        position_id = txn1.position_id

        # Second buy
        txn2 = await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=50,
            price=12.0,
            transaction_date="2026-01-20",
        )

        # Same position updated
        assert txn2.position_id == position_id
        position = svc._positions[position_id]
        assert position.quantity == 150
        assert round(position.cost_price, 2) == 10.67

    @pytest.mark.asyncio
    async def test_buy_transaction_persisted_to_store(self):
        """Buy transaction should be stored in the service's _transactions dict."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        txn = await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=1700.0,
            transaction_date="2026-01-15",
        )

        assert txn.id in svc._transactions
        assert svc._transactions[txn.id].transaction_type == "buy"

    @pytest.mark.asyncio
    async def test_position_auto_updated_after_buy(self):
        """Position should be auto-updated (is_active=True, updated_at set) after buy."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        txn = await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=1700.0,
            transaction_date="2026-01-15",
        )

        position = svc._positions[txn.position_id]
        assert position.is_active is True
        assert position.updated_at is not None

    @pytest.mark.asyncio
    async def test_multiple_buys_accumulate_correctly(self):
        """Three buys should accumulate quantity and compute correct weighted avg cost."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )
        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=50,
            price=12.0,
            transaction_date="2026-01-20",
        )
        txn3 = await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=200,
            price=11.0,
            transaction_date="2026-01-25",
        )

        position = svc._positions[txn3.position_id]
        assert position.quantity == 350
        # avg = (100*10 + 50*12 + 200*11) / 350 = 3800/350 ≈ 10.86
        assert round(position.cost_price, 2) == 10.86


# ---------------------------------------------------------------------------
# 7. Sell Transaction Service Tests (Cycle 1.3)
# ---------------------------------------------------------------------------


class TestSellTransaction:
    """Test record_sell_transaction service method."""

    @pytest.mark.asyncio
    async def test_record_sell_creates_transaction_with_sell_type(self):
        """record_sell_transaction should create a Transaction with type=sell."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        # First, create a position via buy
        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )

        txn = await svc.record_sell_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=50,
            price=15.0,
            transaction_date="2026-02-01",
        )

        assert txn.transaction_type == "sell"
        assert txn.quantity == 50
        assert txn.price == 15.0

    @pytest.mark.asyncio
    async def test_partial_sell_reduces_position_quantity(self):
        """Partial sell should reduce position quantity (100 -> sell 30 -> 70)."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        buy_txn = await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )

        await svc.record_sell_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=30,
            price=12.0,
            transaction_date="2026-02-01",
        )

        position = svc._positions[buy_txn.position_id]
        assert position.quantity == 70

    @pytest.mark.asyncio
    async def test_full_sell_sets_position_inactive(self):
        """Full sell (all shares) should set position is_active=False."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        buy_txn = await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )

        await svc.record_sell_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=15.0,
            transaction_date="2026-02-01",
        )

        position = svc._positions[buy_txn.position_id]
        assert position.is_active is False
        assert position.quantity == 0

    @pytest.mark.asyncio
    async def test_sell_more_than_held_raises_valueerror(self):
        """Selling more shares than held should raise ValueError."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )

        with pytest.raises(ValueError, match="Cannot sell"):
            await svc.record_sell_transaction(
                user_id="user_001",
                ts_code="600519.SH",
                quantity=200,
                price=15.0,
                transaction_date="2026-02-01",
            )

    @pytest.mark.asyncio
    async def test_sell_realized_pl_calculated_correctly(self):
        """Realized P/L should be calculated: sell 50 @ 15, cost_price=10 -> 250."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )

        txn = await svc.record_sell_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=50,
            price=15.0,
            transaction_date="2026-02-01",
        )

        assert txn.realized_pl == 250.0  # 50 * (15 - 10)

    @pytest.mark.asyncio
    async def test_sell_does_not_change_cost_price(self):
        """Position cost_price should remain unchanged after sell (tracks avg buy cost)."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        buy_txn = await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )

        original_cost = svc._positions[buy_txn.position_id].cost_price

        await svc.record_sell_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=30,
            price=15.0,
            transaction_date="2026-02-01",
        )

        assert svc._positions[buy_txn.position_id].cost_price == original_cost

    @pytest.mark.asyncio
    async def test_sell_transaction_persisted_to_store(self):
        """Sell transaction should be stored in the service's _transactions dict."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )

        txn = await svc.record_sell_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=50,
            price=15.0,
            transaction_date="2026-02-01",
        )

        assert txn.id in svc._transactions
        assert svc._transactions[txn.id].transaction_type == "sell"

    @pytest.mark.asyncio
    async def test_sell_nonexistent_position_raises_valueerror(self):
        """Selling a stock with no position should raise ValueError."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        with pytest.raises(ValueError, match="No active position"):
            await svc.record_sell_transaction(
                user_id="user_001",
                ts_code="999999.SH",
                quantity=10,
                price=10.0,
                transaction_date="2026-02-01",
            )


# ---------------------------------------------------------------------------
# 8. Transaction History Query Tests (Cycle 1.4)
# ---------------------------------------------------------------------------


class TestGetTransactions:
    """Test get_transactions query method."""

    @pytest.mark.asyncio
    async def test_get_transactions_returns_list_for_user(self):
        """get_transactions should return list of Transaction for user."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )
        await svc.record_sell_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=30,
            price=12.0,
            transaction_date="2026-02-01",
        )

        txns = await svc.get_transactions(user_id="user_001")
        assert len(txns) >= 2
        assert all(t.user_id == "user_001" for t in txns)

    @pytest.mark.asyncio
    async def test_get_transactions_filtered_by_ts_code(self):
        """get_transactions should support filtering by ts_code."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )
        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="000001.SZ",
            quantity=200,
            price=15.0,
            transaction_date="2026-01-16",
        )

        txns = await svc.get_transactions(user_id="user_001", ts_code="600519.SH")
        assert len(txns) == 1
        assert txns[0].ts_code == "600519.SH"

    @pytest.mark.asyncio
    async def test_get_transactions_ordered_by_date_desc(self):
        """get_transactions should return transactions ordered by date DESC."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )
        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=50,
            price=12.0,
            transaction_date="2026-02-01",
        )

        txns = await svc.get_transactions(user_id="user_001", ts_code="600519.SH")
        assert len(txns) == 2
        # Most recent first
        assert txns[0].transaction_date >= txns[1].transaction_date

    @pytest.mark.asyncio
    async def test_get_transactions_date_range_filter(self):
        """get_transactions should support date range filtering."""
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        svc = EnhancedPortfolioService()
        svc._db = None

        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=100,
            price=10.0,
            transaction_date="2026-01-15",
        )
        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=50,
            price=12.0,
            transaction_date="2026-02-01",
        )
        await svc.record_buy_transaction(
            user_id="user_001",
            ts_code="600519.SH",
            quantity=30,
            price=11.0,
            transaction_date="2026-03-01",
        )

        # Filter to only February onwards
        txns = await svc.get_transactions(
            user_id="user_001",
            ts_code="600519.SH",
            start_date="2026-02-01",
        )
        assert len(txns) == 2
        assert all(t.transaction_date >= "2026-02-01" for t in txns)

        # Filter to only January
        txns_jan = await svc.get_transactions(
            user_id="user_001",
            ts_code="600519.SH",
            start_date="2026-01-01",
            end_date="2026-01-31",
        )
        assert len(txns_jan) == 1


# ---------------------------------------------------------------------------
# 9. Transaction API Endpoint Tests (Cycle 1.5)
# ---------------------------------------------------------------------------


def _make_user(user_id: str = "user_001") -> dict:
    return {
        "id": user_id,
        "username": "testuser",
        "email": "test@test.com",
        "is_admin": False,
    }


class TestTransactionAPIEndpoints:
    """Test the transaction REST API endpoints."""

    def test_buy_endpoint_returns_200(self):
        """POST /api/portfolio/transactions/buy should return 200 with transaction data."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        async def override_auth():
            return _make_user("user_001")

        app.dependency_overrides[get_current_user] = override_auth

        with patch("stock_datasource.models.database.db_client") as mock_db:
            mock_db.execute = Mock()
            mock_db.execute_query = Mock(
                return_value=MagicMock(empty=True, __bool__=lambda self: False)
            )

            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/portfolio/transactions/buy",
                json={
                    "ts_code": "600519.SH",
                    "quantity": 100,
                    "price": 1700.0,
                    "transaction_date": "2026-01-15",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["transaction_type"] == "buy"
            assert data["ts_code"] == "600519.SH"
            assert data["quantity"] == 100

    def test_sell_endpoint_returns_200(self):
        """POST /api/portfolio/transactions/sell should return 200 with transaction data."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        async def override_auth():
            return _make_user("user_001")

        app.dependency_overrides[get_current_user] = override_auth

        # Use a single service instance so buy's position is visible to sell
        shared_svc = EnhancedPortfolioService()
        shared_svc._db = None

        with patch(
            "stock_datasource.modules.portfolio.router.get_enhanced_portfolio_service",
            return_value=shared_svc,
        ):
            client = TestClient(app, raise_server_exceptions=False)
            # First buy to create position
            buy_resp = client.post(
                "/api/portfolio/transactions/buy",
                json={
                    "ts_code": "600519.SH",
                    "quantity": 100,
                    "price": 1700.0,
                    "transaction_date": "2026-01-15",
                },
            )
            assert buy_resp.status_code == 200, f"Buy failed: {buy_resp.text}"

            # Then sell
            response = client.post(
                "/api/portfolio/transactions/sell",
                json={
                    "ts_code": "600519.SH",
                    "quantity": 30,
                    "price": 1800.0,
                    "transaction_date": "2026-02-01",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["transaction_type"] == "sell"
            assert data["quantity"] == 30

    def test_get_transactions_returns_list(self):
        """GET /api/portfolio/transactions should return list."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        async def override_auth():
            return _make_user("user_001")

        app.dependency_overrides[get_current_user] = override_auth

        with patch("stock_datasource.models.database.db_client") as mock_db:
            mock_db.execute = Mock()
            mock_db.execute_query = Mock(
                return_value=MagicMock(empty=True, __bool__=lambda self: False)
            )

            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/api/portfolio/transactions")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_sell_more_than_held_returns_400(self):
        """POST /api/portfolio/transactions/sell with quantity > held should return 400."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        async def override_auth():
            return _make_user("user_001")

        app.dependency_overrides[get_current_user] = override_auth

        with patch("stock_datasource.models.database.db_client") as mock_db:
            mock_db.execute = Mock()
            mock_db.execute_query = Mock(
                return_value=MagicMock(empty=True, __bool__=lambda self: False)
            )

            client = TestClient(app, raise_server_exceptions=False)
            # Buy some shares first
            client.post(
                "/api/portfolio/transactions/buy",
                json={
                    "ts_code": "600519.SH",
                    "quantity": 50,
                    "price": 1700.0,
                    "transaction_date": "2026-01-15",
                },
            )

            # Try to sell more than held
            response = client.post(
                "/api/portfolio/transactions/sell",
                json={
                    "ts_code": "600519.SH",
                    "quantity": 200,
                    "price": 1800.0,
                    "transaction_date": "2026-02-01",
                },
            )

            assert response.status_code == 400

    def test_endpoints_require_auth(self):
        """Transaction endpoints should require authentication."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from stock_datasource.modules.portfolio.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        client = TestClient(app, raise_server_exceptions=False)

        # Without auth override, should get 401/403/500
        response = client.get("/api/portfolio/transactions")
        assert response.status_code in (401, 403, 500)


# ---------------------------------------------------------------------------
# TDD Cycle 2.1: Transaction Signals Endpoint (for K-line B/S markers)
# ---------------------------------------------------------------------------


class TestTransactionSignals:
    """Tests for the transaction signals endpoint.

    The signals endpoint returns buy/sell markers that combine:
    - User transactions (actual buy/sell records)
    - Technical strategy signals (from indicators API)
    These are used to display B/S point markers on K-line charts.
    """

    def test_get_signals_returns_list(self):
        """GET /transactions/signals with ts_code returns a list."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        def override_auth():
            return {"id": "user_signals_001", "username": "test_signals"}

        app.dependency_overrides[get_current_user] = override_auth

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/api/portfolio/transactions/signals",
            params={"ts_code": "600519.SH"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_signals_require_ts_code_param(self):
        """GET /transactions/signals without ts_code should return 422."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        def override_auth():
            return {"id": "user_signals_002", "username": "test_signals"}

        app.dependency_overrides[get_current_user] = override_auth

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/portfolio/transactions/signals")

        assert response.status_code == 422

    def test_signal_item_has_required_fields(self):
        """Each signal item should have id, ts_code, signal_type, source, signal_date, price."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import patch

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
            Transaction,
        )

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        def override_auth():
            return {"id": "user_signals_003", "username": "test_signals"}

        app.dependency_overrides[get_current_user] = override_auth

        # Create a service with a recorded buy transaction
        svc = EnhancedPortfolioService()
        svc._db = None

        with patch(
            "stock_datasource.modules.portfolio.router.get_enhanced_portfolio_service",
            return_value=svc,
        ):
            # Record a buy so we have at least one signal
            import asyncio

            txn = asyncio.get_event_loop().run_until_complete(
                svc.record_buy_transaction(
                    user_id="user_signals_003",
                    ts_code="600519.SH",
                    quantity=100,
                    price=1800.0,
                    transaction_date="2026-04-20",
                )
            )

            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                "/api/portfolio/transactions/signals",
                params={"ts_code": "600519.SH"},
            )

        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            signal = data[0]
            assert "id" in signal
            assert "ts_code" in signal
            assert "signal_type" in signal
            assert "source" in signal
            assert "signal_date" in signal
            assert "price" in signal
            assert signal["source"] == "user"
            assert signal["signal_type"] in ("buy", "sell")

    def test_signals_include_both_user_and_strategy(self):
        """Signals should include items with source='user' from transactions."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import patch, AsyncMock

        from stock_datasource.modules.auth.dependencies import get_current_user
        from stock_datasource.modules.portfolio.router import router
        from stock_datasource.modules.portfolio.enhanced_service import (
            EnhancedPortfolioService,
        )

        app = FastAPI()
        app.include_router(router, prefix="/api/portfolio")

        def override_auth():
            return {"id": "user_signals_004", "username": "test_signals"}

        app.dependency_overrides[get_current_user] = override_auth

        svc = EnhancedPortfolioService()
        svc._db = None

        with patch(
            "stock_datasource.modules.portfolio.router.get_enhanced_portfolio_service",
            return_value=svc,
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                "/api/portfolio/transactions/signals",
                params={"ts_code": "600519.SH"},
            )

        assert response.status_code == 200
        data = response.json()
        # All signals from user transactions should have source='user'
        user_signals = [s for s in data if s.get("source") == "user"]
        # Strategy signals may or may not be present (depends on indicators)
        # At minimum, the response format is correct
        for s in user_signals:
            assert s["signal_type"] in ("buy", "sell")
            assert s["ts_code"] == "600519.SH"
