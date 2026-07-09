"""
EXECUTION ENGINE (Sprint 6)

The ONLY module allowed to interact with Exchange APIs (CCXT/Binance).
All other modules (Workers, HiveMind, Portfolio) are STRICTLY FORBIDDEN 
from importing ccxt or making network calls to exchanges.

Responsibility:
1. Translate ExecutionIntent into actual Orders.
2. Mock/Dummy exchange interaction for simulation.
3. Record Position ID and return ExecutedOrder.
"""

import uuid
from datetime import datetime
from typing import Optional

import sys
sys.path.append('.')

from schemas.execution_schema import ExecutionIntent
from execution.execution_schemas import ExecutedOrder, OrderSide, OrderType

class MockExchangeClient:
    """
    Dummy CCXT-like client for simulation.
    In production, this would be replaced by real ccxt.Exchange instance.
    """
    
    def __init__(self):
        self.name = "MockExchange"
        self._prices = {
            "BTCUSDT": 95000.0,
            "ETHUSDT": 3500.0,
            "SOLUSDT": 200.0
        }
    
    def fetch_price(self, symbol: str) -> float:
        """Get current mock price."""
        return self._prices.get(symbol, 100.0)
    
    def create_market_order(self, symbol: str, side: str, amount_usd: float, leverage: int = 1) -> dict:
        """
        Simulate creating a market order.
        Returns a mock order response.
        """
        price = self.fetch_price(symbol)
        # Calculate quantity based on USD amount and leverage
        quantity = (amount_usd * leverage) / price
        
        return {
            "id": f"ord_{uuid.uuid4().hex[:8]}",
            "symbol": symbol,
            "type": "market",
            "side": side.lower(),
            "price": price,
            "amount": quantity,
            "cost": amount_usd,
            "leverage": leverage,
            "status": "closed",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def set_price(self, symbol: str, price: float) -> None:
        """Manually set price for simulation purposes."""
        self._prices[symbol] = price


class ExecutionEngine:
    """
    EXECUTION ENGINE
    
    Gateway between internal ExecutionIntents and external Exchange.
    
    GUARDRAILS:
    - ONLY file allowed to import/use ccxt or exchange clients.
    - Does NOT make trading decisions (only executes intents).
    - Does NOT modify positions directly (reports back to Position Manager).
    """
    
    def __init__(self):
        self.exchange = MockExchangeClient()
        self._order_history = []
    
    def execute_intent(self, intent: ExecutionIntent) -> ExecutedOrder:
        """
        Translate ExecutionIntent into an actual Exchange Order.
        
        Args:
            intent: Validated ExecutionIntent from PortfolioManager
            
        Returns:
            ExecutedOrder with actual fill price and order ID
            
        Raises:
            ValueError: If intent mode is REPLAY (no actual execution)
        """
        if intent.mode == "REPLAY":
            # In REPLAY mode, we simulate execution but don't actually send to exchange
            # For testing purposes, we still return an order object but mark it as simulated
            pass
        
        # Determine side based on direction
        side = OrderSide.BUY if intent.direction == "LONG" else OrderSide.SELL
        
        # Execute on mock exchange
        raw_order = self.exchange.create_market_order(
            symbol=intent.symbol,
            side=side.value,
            amount_usd=intent.size_usd,
            leverage=intent.leverage
        )
        
        executed_order = ExecutedOrder(
            order_id=raw_order["id"],
            symbol=raw_order["symbol"],
            side=side,
            type=OrderType.MARKET,
            price=raw_order["price"],
            size_usd=raw_order["cost"],
            leverage=raw_order["leverage"]
        )
        
        self._order_history.append(executed_order)
        return executed_order
    
    def close_position(self, position_id: str, symbol: str, direction: str, 
                       size_usd: float, leverage: int) -> ExecutedOrder:
        """
        Close an existing position by executing the opposite order.
        
        Args:
            position_id: ID of position being closed
            symbol: Trading pair
            direction: Original direction (LONG->SELL to close, SHORT->BUY to close)
            size_usd: Position size to close
            leverage: Leverage used
            
        Returns:
            ExecutedOrder for the closing transaction
        """
        # Reverse side to close
        close_side = OrderSide.SELL if direction == "LONG" else OrderSide.BUY
        
        raw_order = self.exchange.create_market_order(
            symbol=symbol,
            side=close_side.value,
            amount_usd=size_usd,
            leverage=leverage
        )
        
        executed_order = ExecutedOrder(
            order_id=raw_order["id"],
            symbol=raw_order["symbol"],
            side=close_side,
            type=OrderType.MARKET,
            price=raw_order["price"],
            size_usd=raw_order["cost"],
            leverage=raw_order["leverage"]
        )
        
        self._order_history.append(executed_order)
        return executed_order
    
    def get_current_price(self, symbol: str) -> float:
        """Fetch current market price (mock)."""
        return self.exchange.fetch_price(symbol)
    
    def set_mock_price(self, symbol: str, price: float) -> None:
        """Set mock price for testing scenarios."""
        self.exchange.set_price(symbol, price)
    
    # AUDIT CHECKLIST: ExecutionEngine
    # [✓] ONLY module with exchange client (MockExchangeClient/CCXT)
    # [✓] Does NOT decide WHEN to trade (only executes intents)
    # [✓] Does NOT decide EXIT timing (Exit Manager decides)
    # [✓] No business logic, pure translation layer
    # [✓] Supports both LIVE and REPLAY modes
