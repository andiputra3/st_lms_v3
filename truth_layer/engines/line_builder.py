"""
ST-LMS v3 - Line Builder Engine
Groups SupertrendPoints into SupertrendLines based on price proximity.
Rules:
- If new point price is within tolerance (ATR * 0.3 or 0.2%) of active line, add as member with "MOVE" event.
- If price jumps beyond tolerance, close old line and create new line with "CREATE" event.
"""
from typing import List, Optional, Tuple
from datetime import datetime
import sys
sys.path.insert(0, '/workspace')

from truth_layer.schemas import LineVersion, SupertrendLine
# Import from Sprint 1 modules
from supertrend_point import SupertrendPoint


class LineBuilder:
    """
    Builds SupertrendLines from a stream of SupertrendPoints.
    Maintains active lines for SUPPORT and RESISTANCE separately.
    """
    
    def __init__(self, tolerance_pct: float = 0.002, tolerance_atr_mult: float = 0.3):
        """
        Initialize Line Builder.
        
        Args:
            tolerance_pct: Price tolerance as percentage (default 0.2%)
            tolerance_atr_mult: ATR multiplier for tolerance (default 0.3)
        """
        self.tolerance_pct = tolerance_pct
        self.tolerance_atr_mult = tolerance_atr_mult
        self.active_lines: dict[str, Optional[SupertrendLine]] = {
            "SUPPORT": None,
            "RESISTANCE": None
        }
        self.completed_lines: List[SupertrendLine] = []
        self.line_counter: dict[str, int] = {"SUPPORT": 0, "RESISTANCE": 0}
    
    def _calculate_tolerance(self, base_price: float, current_atr: float) -> float:
        """
        Calculate dynamic tolerance based on percentage and ATR.
        Returns the larger of the two tolerances.
        """
        pct_tolerance = base_price * self.tolerance_pct
        atr_tolerance = current_atr * self.tolerance_atr_mult
        return max(pct_tolerance, atr_tolerance)
    
    def _generate_line_id(self, line_type: str, time_id: str) -> str:
        """
        Generate unique line ID: L{time_id}-{type_short}-{counter}
        """
        type_short = "SUP" if line_type == "SUPPORT" else "RES"
        self.line_counter[line_type] += 1
        return f"L{time_id[1:]}-{type_short}-{self.line_counter[line_type]:03d}"
    
    def _is_price_within_tolerance(self, price1: float, price2: float, atr: float) -> bool:
        """
        Check if two prices are within tolerance range.
        """
        tolerance = self._calculate_tolerance(price1, atr)
        return abs(price1 - price2) <= tolerance
    
    def _close_active_line(self, line_type: str) -> None:
        """
        Move active line to completed lines list.
        """
        if self.active_lines[line_type] is not None:
            self.completed_lines.append(self.active_lines[line_type])
            self.active_lines[line_type] = None
    
    def process_point(self, point: SupertrendPoint, current_atr: float) -> None:
        """
        Process a single SupertrendPoint and update lines accordingly.
        
        Args:
            point: The SupertrendPoint to process
            current_atr: Current ATR value for tolerance calculation
        """
        line_type = point.type  # "SUPPORT" or "RESISTANCE"
        active_line = self.active_lines[line_type]
        
        if active_line is None:
            # No active line, create new one
            line_id = self._generate_line_id(line_type, point.point_id)
            version = LineVersion(
                point_id=point.point_id,
                price=point.price,
                event="CREATE",
                time_wib=point.time_wib
            )
            self.active_lines[line_type] = SupertrendLine(
                line_id=line_id,
                type=line_type,
                current_price=point.price,
                strength=1,
                versions=[version],
                members=[point.point_id]
            )
        else:
            # Check if point price is within tolerance of active line
            if self._is_price_within_tolerance(active_line.current_price, point.price, current_atr):
                # Add to existing line as MOVE event
                version = LineVersion(
                    point_id=point.point_id,
                    price=point.price,
                    event="MOVE",
                    time_wib=point.time_wib
                )
                active_line.versions.append(version)
                active_line.members.append(point.point_id)
                active_line.current_price = point.price
                active_line.strength += 1
            else:
                # Price jumped too far, close old line and create new one
                self._close_active_line(line_type)
                
                line_id = self._generate_line_id(line_type, point.point_id)
                version = LineVersion(
                    point_id=point.point_id,
                    price=point.price,
                    event="CREATE",
                    time_wib=point.time_wib
                )
                self.active_lines[line_type] = SupertrendLine(
                    line_id=line_id,
                    type=line_type,
                    current_price=point.price,
                    strength=1,
                    versions=[version],
                    members=[point.point_id]
                )
    
    def process_points(self, points: List[SupertrendPoint], atr_values: List[float]) -> List[SupertrendLine]:
        """
        Process a list of SupertrendPoints and return all completed lines.
        
        Args:
            points: List of SupertrendPoints to process
            atr_values: List of ATR values corresponding to each point
        
        Returns:
            List of all completed SupertrendLines (including currently active ones)
        """
        if len(points) != len(atr_values):
            raise ValueError("Points and ATR values must have same length")
        
        for point, atr in zip(points, atr_values):
            self.process_point(point, atr)
        
        # Return completed lines + currently active lines
        result = self.completed_lines.copy()
        for line_type in ["SUPPORT", "RESISTANCE"]:
            if self.active_lines[line_type] is not None:
                result.append(self.active_lines[line_type])
        
        return result
    
    def get_active_lines(self) -> dict[str, Optional[SupertrendLine]]:
        """
        Get currently active lines for both SUPPORT and RESISTANCE.
        """
        return self.active_lines.copy()
    
    def reset(self) -> None:
        """
        Reset the builder state.
        """
        self.active_lines = {"SUPPORT": None, "RESISTANCE": None}
        self.completed_lines = []
        self.line_counter = {"SUPPORT": 0, "RESISTANCE": 0}
