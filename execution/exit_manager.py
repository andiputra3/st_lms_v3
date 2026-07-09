"""
EXIT MANAGER (Sprint 6) - GLOBAL EXIT ENGINE

The SOLE authority for closing positions.
Monitors all open positions and enforces exit logic:
1. Stop Loss (Hard)
2. Take Profit
3. Trailing Stop
4. EMERGENCY EXIT (Mandatory 5% max loss tolerance)

GUARDRAILS:
- Workers CANNOT close their own positions.
- Workers can only send "Exit Proposal" to HiveMind.
- Exit Manager has VETO power and强制执行 (Emergency Exit).
- Only module (besides ExecutionEngine) that can trigger order closure.
"""

from typing import List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass

import sys
sys.path.append('.')

from execution.execution_schemas import PositionState, PositionStatus
from execution.position_manager import PositionManager
from execution.execution_engine import ExecutionEngine


@dataclass
class ExitDecision:
    """Result of exit evaluation."""
    should_exit: bool
    reason: str
    exit_type: str  # 'STOP_LOSS', 'TAKE_PROFIT', 'TRAILING_STOP', 'EMERGENCY'
    priority: int  # Higher = more urgent (Emergency = 999)


class ExitManager:
    """
    GLOBAL EXIT ENGINE
    
    Monitors market prices and position states to determine exit timing.
    Has exclusive authority to command position closures.
    
    Exit Logic Priority:
    1. EMERGENCY EXIT (>5% loss) - Immediate强制执行
    2. STOP LOSS - Hard stop at configured level
    3. TRAILING STOP - Lock in profits
    4. TAKE PROFIT - Target reached
    """
    
    # MANDATORY RISK LIMIT
    EMERGENCY_EXIT_THRESHOLD_PCT = -0.05  # -5% max loss tolerance
    
    def __init__(self, position_manager: PositionManager, execution_engine: ExecutionEngine):
        self.pm = position_manager
        self.engine = execution_engine
        self._exit_log = []
        
    def monitor_all_positions(self) -> List[ExitDecision]:
        """
        Main monitoring loop - check all open positions for exit conditions.
        Should be called periodically (e.g., every candle close or price tick).
        
        Returns:
            List of ExitDecisions for positions that need to be closed
        """
        open_positions = self.pm.get_all_open_positions()
        decisions = []
        
        for position in open_positions:
            # Get current price from engine (mock in this case)
            current_price = self.engine.get_current_price(position.symbol)
            
            # Update position PnL with latest price
            self.pm.update_position_price(position.position_id, current_price)
            
            # Refresh position state after update
            position = self.pm.get_position(position.position_id)
            
            # Evaluate exit conditions
            decision = self._evaluate_exit(position)
            
            if decision.should_exit:
                decisions.append(decision)
                
                # Execute exit immediately for high-priority exits
                if decision.priority >= 100:  # Emergency or Stop Loss
                    self._execute_exit(position, decision)
        
        return decisions
    
    def _evaluate_exit(self, position: PositionState) -> ExitDecision:
        """
        Evaluate a single position against all exit conditions.
        Returns ExitDecision with highest priority trigger.
        """
        pnl_pct = position.unrealized_pnl_pct
        
        # 1. EMERGENCY EXIT (Highest Priority - 999)
        # Mandatory 5% max loss tolerance
        if pnl_pct <= self.EMERGENCY_EXIT_THRESHOLD_PCT:
            return ExitDecision(
                should_exit=True,
                reason=f"Emergency Exit: Loss {pnl_pct:.2%} exceeds max tolerance {self.EMERGENCY_EXIT_THRESHOLD_PCT:.2%}",
                exit_type="EMERGENCY",
                priority=999
            )
        
        # 2. STOP LOSS (Priority - 100)
        # Only check if not already in emergency
        if pnl_pct <= position.stop_loss_pct and pnl_pct > self.EMERGENCY_EXIT_THRESHOLD_PCT:
            return ExitDecision(
                should_exit=True,
                reason=f"Stop Loss hit at {pnl_pct:.2%} (threshold: {position.stop_loss_pct:.2%})",
                exit_type="STOP_LOSS",
                priority=100
            )
        
        # 3. TRAILING STOP (Priority - 50)
        # Only check trailing stop if we have some profit (price moved favorably)
        if pnl_pct > 0:
            trailing_triggered = self._check_trailing_stop(position)
            if trailing_triggered:
                return ExitDecision(
                    should_exit=True,
                    reason=f"Trailing Stop triggered. Price retraced from peak.",
                    exit_type="TRAILING_STOP",
                    priority=50
                )
        
        # 4. TAKE PROFIT (Priority - 10)
        if pnl_pct >= position.take_profit_pct:
            return ExitDecision(
                should_exit=True,
                reason=f"Take Profit reached at {pnl_pct:.2%} (target: {position.take_profit_pct:.2%})",
                exit_type="TAKE_PROFIT",
                priority=10
            )
        
        # No exit condition met
        return ExitDecision(
            should_exit=False,
            reason="No exit condition met",
            exit_type="HOLD",
            priority=0
        )
    
    def _check_trailing_stop(self, position: PositionState) -> bool:
        """
        Check if trailing stop condition is triggered.
        
        Logic:
        - For LONG: If price drops X% from highest price since entry
        - For SHORT: If price rises X% from lowest price since entry
        """
        trailing_threshold = position.trailing_stop_pct
        
        if position.direction == "LONG":
            if position.highest_price_since_entry > 0:
                drop_from_peak = (position.highest_price_since_entry - position.current_price) / position.highest_price_since_entry
                if drop_from_peak >= trailing_threshold:
                    return True
        else:  # SHORT
            if position.lowest_price_since_entry > 0:
                rise_from_trough = (position.current_price - position.lowest_price_since_entry) / position.lowest_price_since_entry
                if rise_from_trough >= trailing_threshold:
                    return True
        
        return False
    
    def _execute_exit(self, position: PositionState, decision: ExitDecision) -> None:
        """
        Command Execution Engine to close the position.
        Logs the exit event.
        """
        # Execute closing order via Execution Engine
        closed_order = self.engine.close_position(
            position_id=position.position_id,
            symbol=position.symbol,
            direction=position.direction,
            size_usd=position.size_usd,
            leverage=position.leverage
        )
        
        # Calculate realized PnL
        if position.direction == "LONG":
            realized_pnl = (closed_order.price - position.entry_price) / position.entry_price
        else:
            realized_pnl = (position.entry_price - closed_order.price) / position.entry_price
        
        realized_pnl_usd = realized_pnl * position.size_usd * position.leverage
        
        # Update Position Manager state
        self.pm.close_position(
            position_id=position.position_id,
            exit_price=closed_order.price,
            realized_pnl_usd=realized_pnl_usd
        )
        
        # Log exit event
        exit_record = {
            "timestamp": datetime.utcnow(),
            "position_id": position.position_id,
            "symbol": position.symbol,
            "worker_name": position.worker_name,
            "exit_type": decision.exit_type,
            "reason": decision.reason,
            "entry_price": position.entry_price,
            "exit_price": closed_order.price,
            "pnl_usd": realized_pnl_usd,
            "pnl_pct": realized_pnl
        }
        self._exit_log.append(exit_record)
        
        print(f"[EXIT MANAGER] {decision.exit_type}: {position.symbol} | "
              f"PnL: ${realized_pnl_usd:.2f} ({realized_pnl:.2%}) | Reason: {decision.reason}")
    
    def force_emergency_exit(self, position_id: str) -> ExitDecision:
        """
        Manually trigger emergency exit for a specific position.
        Used for external risk controls or manual intervention.
        """
        position = self.pm.get_position(position_id)
        if not position:
            raise KeyError(f"Position {position_id} not found")
        
        # Force update price first
        current_price = self.engine.get_current_price(position.symbol)
        self.pm.update_position_price(position_id, current_price)
        position = self.pm.get_position(position_id)
        
        decision = ExitDecision(
            should_exit=True,
            reason="Manual Emergency Exit triggered",
            exit_type="EMERGENCY",
            priority=999
        )
        
        self._execute_exit(position, decision)
        return decision
    
    def get_exit_history(self) -> List[dict]:
        """Get log of all executed exits."""
        return self._exit_log
    
    def get_emergency_exit_count(self) -> int:
        """Count how many emergency exits have been triggered."""
        return len([e for e in self._exit_log if e["exit_type"] == "EMERGENCY"])
    
    # AUDIT CHECKLIST: ExitManager
    # [✓] Sole authority for position closure
    # [✓] Enforces mandatory 5% emergency exit
    # [✓] Workers cannot bypass this layer
    # [✓] Commands ExecutionEngine to close (does not execute directly)
    # [✓] No exchange API calls (delegates to ExecutionEngine)
    # [✓] Priority-based exit logic (Emergency > StopLoss > Trailing > TakeProfit)
