"""
Schemas for Execution Layer (Sprint 6)
Defines Position state and Order structures.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"

class ExecutedOrder(BaseModel):
    """Represents an order executed by the Execution Engine."""
    order_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    price: float
    size_usd: float
    leverage: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "ord_12345",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "MARKET",
                "price": 95000.0,
                "size_usd": 10.0,
                "leverage": 5
            }
        }

class PositionState(BaseModel):
    """
    Global state of an open position.
    Tracked by Position Manager, monitored by Exit Manager.
    """
    position_id: str
    intent_id: str  # Link back to ExecutionIntent
    symbol: str
    direction: Literal["LONG", "SHORT"]
    worker_name: str
    
    # Entry Details
    entry_price: float
    size_usd: float
    leverage: int
    
    # Current State
    current_price: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    exit_price: Optional[float] = None
    
    # PnL Tracking
    unrealized_pnl_usd: float = 0.0
    unrealized_pnl_pct: float = 0.0
    realized_pnl_usd: Optional[float] = None
    realized_pnl_pct: Optional[float] = None
    
    # Exit Strategy Parameters (set at entry)
    stop_loss_pct: float = -0.05  # Default 5% hard stop
    take_profit_pct: float = 0.10 # Default 10% target
    trailing_stop_pct: float = 0.03 # 3% trailing
    highest_price_since_entry: float = 0.0 # For trailing calc
    lowest_price_since_entry: float = 0.0 # For trailing calc
    
    def update_pnl(self, current_price: float) -> None:
        """Calculate unrealized PnL based on current price."""
        self.current_price = current_price
        
        # Update high/low for trailing stop logic
        if self.highest_price_since_entry == 0.0 or current_price > self.highest_price_since_entry:
            self.highest_price_since_entry = current_price
        if self.lowest_price_since_entry == 0.0 or current_price < self.lowest_price_since_entry:
            self.lowest_price_since_entry = current_price
            
        # Calculate PnL
        if self.direction == "LONG":
            price_diff_pct = (current_price - self.entry_price) / self.entry_price
        else: # SHORT
            price_diff_pct = (self.entry_price - current_price) / self.entry_price
            
        self.unrealized_pnl_pct = price_diff_pct
        self.unrealized_pnl_usd = price_diff_pct * self.size_usd * self.leverage

    class Config:
        json_schema_extra = {
            "example": {
                "position_id": "pos_abc123",
                "intent_id": "exec_xyz789",
                "symbol": "BTCUSDT",
                "direction": "LONG",
                "worker_name": "PullbackWorker_v1",
                "entry_price": 95000.0,
                "size_usd": 10.0,
                "leverage": 5,
                "current_price": 96000.0,
                "status": "OPEN",
                "unrealized_pnl_usd": 50.0,
                "unrealized_pnl_pct": 0.0105
            }
        }
