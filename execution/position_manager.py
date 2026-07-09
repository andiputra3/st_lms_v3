"""
POSITION MANAGER (Sprint 6)

Global service for tracking ALL open positions from ALL workers.
Maintains state of positions and provides interface for Exit Manager to monitor.

Responsibilities:
1. Register new positions when ExecutionEngine fills an order.
2. Track entry price, size, worker name, current PnL.
3. Provide real-time position state to Exit Manager.
4. Update position status when closed.
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime

import sys
sys.path.append('.')

from execution.execution_schemas import PositionState, PositionStatus
from schemas.execution_schema import ExecutionIntent
from execution.execution_engine import ExecutedOrder


class PositionManager:
    """
    POSITION MANAGER
    
    Central registry of all active positions.
    Read-only for Exit Manager (monitors), Write-enabled for Execution Engine.
    
    GUARDRAILS:
    - Does NOT decide when to exit (Exit Manager decides).
    - Does NOT interact with exchange directly.
    - Pure state management service.
    """
    
    def __init__(self):
        # Key: position_id, Value: PositionState
        self._positions: Dict[str, PositionState] = {}
        # Key: intent_id, Value: position_id (for lookup)
        self._intent_to_position: Dict[str, str] = {}
        
    def create_position(self, intent: ExecutionIntent, executed_order: ExecutedOrder) -> PositionState:
        """
        Register a new position after successful order execution.
        
        Args:
            intent: Original ExecutionIntent
            executed_order: Order returned by ExecutionEngine
            
        Returns:
            PositionState object for the new position
        """
        position_id = f"pos_{uuid.uuid4().hex[:8]}"
        
        position = PositionState(
            position_id=position_id,
            intent_id=intent.intent_id,
            symbol=intent.symbol,
            direction=intent.direction,
            worker_name=intent.worker_name,
            entry_price=executed_order.price,
            size_usd=intent.size_usd,
            leverage=intent.leverage,
            current_price=executed_order.price,
            highest_price_since_entry=executed_order.price,
            lowest_price_since_entry=executed_order.price
        )
        
        self._positions[position_id] = position
        self._intent_to_position[intent.intent_id] = position_id
        
        return position
    
    def get_position(self, position_id: str) -> Optional[PositionState]:
        """Get position by ID."""
        return self._positions.get(position_id)
    
    def get_position_by_intent(self, intent_id: str) -> Optional[PositionState]:
        """Get position by original intent ID."""
        pos_id = self._intent_to_position.get(intent_id)
        if pos_id:
            return self._positions.get(pos_id)
        return None
    
    def get_all_open_positions(self) -> List[PositionState]:
        """Get all currently open positions."""
        return [p for p in self._positions.values() if p.status == PositionStatus.OPEN]
    
    def update_position_price(self, position_id: str, current_price: float) -> None:
        """
        Update current price and recalculate PnL for a position.
        Called by Exit Manager during market monitoring loop.
        """
        if position_id in self._positions:
            self._positions[position_id].update_pnl(current_price)
    
    def close_position(self, position_id: str, exit_price: float, 
                       realized_pnl_usd: float) -> PositionState:
        """
        Mark a position as closed with final PnL.
        
        Args:
            position_id: ID of position to close
            exit_price: Price at which position was closed
            realized_pnl_usd: Actual PnL realized
            
        Returns:
            Updated PositionState
        """
        if position_id not in self._positions:
            raise KeyError(f"Position {position_id} not found")
        
        position = self._positions[position_id]
        position.status = PositionStatus.CLOSED
        position.exit_price = exit_price
        position.closed_at = datetime.utcnow()
        position.realized_pnl_usd = realized_pnl_usd
        position.realized_pnl_pct = realized_pnl_usd / (position.size_usd * position.leverage)
        position.current_price = exit_price
        
        return position
    
    def get_total_exposure(self) -> float:
        """Calculate total USD exposure across all open positions."""
        total = 0.0
        for pos in self._positions.values():
            if pos.status == PositionStatus.OPEN:
                total += pos.size_usd * pos.leverage
        return total
    
    def get_worker_exposure(self, worker_name: str) -> float:
        """Calculate total exposure for a specific worker."""
        total = 0.0
        for pos in self._positions.values():
            if pos.status == PositionStatus.OPEN and pos.worker_name == worker_name:
                total += pos.size_usd * pos.leverage
        return total
    
    def get_summary(self) -> dict:
        """Get summary statistics of all positions."""
        open_positions = self.get_all_open_positions()
        total_pnl = sum(p.unrealized_pnl_usd for p in open_positions)
        
        return {
            "total_positions": len(self._positions),
            "open_positions": len(open_positions),
            "closed_positions": len([p for p in self._positions.values() if p.status == PositionStatus.CLOSED]),
            "total_exposure_usd": self.get_total_exposure(),
            "total_unrealized_pnl": total_pnl,
            "positions": [
                {
                    "position_id": p.position_id,
                    "symbol": p.symbol,
                    "direction": p.direction,
                    "worker": p.worker_name,
                    "pnl_usd": p.unrealized_pnl_usd,
                    "pnl_pct": p.unrealized_pnl_pct
                }
                for p in open_positions
            ]
        }
    
    # AUDIT CHECKLIST: PositionManager
    # [✓] No exchange API calls
    # [✓] No exit decision logic (only stores state)
    # [✓] Provides read access to Exit Manager
    # [✓] Pure state management service
