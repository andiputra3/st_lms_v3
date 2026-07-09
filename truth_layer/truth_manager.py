"""
ST-LMS v3 - Truth Manager (Read-Only API for Workers)
Provides runtime calculations for distance, slope, and duration.
IMPORTANT: These values are NEVER stored in JSON, only calculated on-demand.
"""
from typing import List, Optional, Tuple
from datetime import datetime
import json
import os
import sys
sys.path.insert(0, '/workspace')

from truth_layer.schemas import SupertrendLine, SupertrendWave


class TruthManager:
    """
    Read-only API for Workers to query the Truth Layer.
    All computed values (distance, slope, duration) are calculated at runtime.
    """
    
    def __init__(self, lines_file: str = "/workspace/truth_layer/storage/lines.json",
                 waves_file: str = "/workspace/truth_layer/storage/waves.json"):
        """
        Initialize Truth Manager with file paths.
        
        Args:
            lines_file: Path to lines JSON storage
            waves_file: Path to waves JSON storage
        """
        self.lines_file = lines_file
        self.waves_file = waves_file
        self._lines_cache: List[SupertrendLine] = []
        self._waves_cache: List[SupertrendWave] = []
        self._load_from_storage()
    
    def _load_from_storage(self) -> None:
        """
        Load lines and waves from JSON files into memory.
        """
        # Load lines
        if os.path.exists(self.lines_file):
            with open(self.lines_file, 'r') as f:
                data = json.load(f)
                self._lines_cache = [SupertrendLine(**line) for line in data]
        
        # Load waves
        if os.path.exists(self.waves_file):
            with open(self.waves_file, 'r') as f:
                data = json.load(f)
                self._waves_cache = [SupertrendWave(**wave) for wave in data]
    
    def reload(self) -> None:
        """
        Force reload data from storage.
        """
        self._lines_cache = []
        self._waves_cache = []
        self._load_from_storage()
    
    def _calculate_distance(self, price1: float, price2: float) -> float:
        """
        Calculate absolute distance between two prices.
        Runtime calculation only - NOT stored in JSON.
        """
        return abs(price1 - price2)
    
    def _calculate_distance_pct(self, price1: float, price2: float) -> float:
        """
        Calculate percentage distance between two prices.
        Runtime calculation only - NOT stored in JSON.
        """
        if price1 == 0:
            return 0.0
        return abs((price2 - price1) / price1) * 100
    
    def _calculate_slope(self, line: SupertrendLine) -> Optional[float]:
        """
        Calculate price slope of a line based on its versions.
        Returns price change per version (simple linear slope).
        Runtime calculation only - NOT stored in JSON.
        """
        if len(line.versions) < 2:
            return 0.0
        
        first_price = line.versions[0].price
        last_price = line.versions[-1].price
        version_count = len(line.versions) - 1
        
        return (last_price - first_price) / version_count
    
    def _calculate_duration(self, line: SupertrendLine) -> int:
        """
        Calculate duration of a line in minutes.
        Runtime calculation only - NOT stored in JSON.
        """
        if len(line.versions) < 2:
            return 0
        
        first_time = line.versions[0].time_wib
        last_time = line.versions[-1].time_wib
        
        delta = last_time - first_time
        return int(delta.total_seconds() / 60)
    
    def get_all_lines(self) -> List[SupertrendLine]:
        """
        Get all loaded lines.
        """
        return self._lines_cache.copy()
    
    def get_all_waves(self) -> List[SupertrendWave]:
        """
        Get all loaded waves.
        """
        return self._waves_cache.copy()
    
    def get_nearest_support(self, current_price: float) -> Optional[Tuple[SupertrendLine, float, float]]:
        """
        Find the nearest SUPPORT line below or at the current price.
        
        Args:
            current_price: Current market price
        
        Returns:
            Tuple of (line, distance, distance_pct) or None if no support found
        """
        supports = [l for l in self._lines_cache if l.type == "SUPPORT"]
        
        if not supports:
            return None
        
        # Find support lines at or below current price
        valid_supports = [(line, self._calculate_distance(current_price, line.current_price)) 
                          for line in supports if line.current_price <= current_price]
        
        if not valid_supports:
            # If no support below, return the closest one anyway
            valid_supports = [(line, self._calculate_distance(current_price, line.current_price)) 
                              for line in supports]
        
        # Sort by distance and return closest
        valid_supports.sort(key=lambda x: x[1])
        nearest_line, distance = valid_supports[0]
        distance_pct = self._calculate_distance_pct(current_price, nearest_line.current_price)
        
        return (nearest_line, distance, distance_pct)
    
    def get_nearest_resistance(self, current_price: float) -> Optional[Tuple[SupertrendLine, float, float]]:
        """
        Find the nearest RESISTANCE line above or at the current price.
        
        Args:
            current_price: Current market price
        
        Returns:
            Tuple of (line, distance, distance_pct) or None if no resistance found
        """
        resistances = [l for l in self._lines_cache if l.type == "RESISTANCE"]
        
        if not resistances:
            return None
        
        # Find resistance lines at or above current price
        valid_resistances = [(line, self._calculate_distance(current_price, line.current_price)) 
                             for line in resistances if line.current_price >= current_price]
        
        if not valid_resistances:
            # If no resistance above, return the closest one anyway
            valid_resistances = [(line, self._calculate_distance(current_price, line.current_price)) 
                                 for line in resistances]
        
        # Sort by distance and return closest
        valid_resistances.sort(key=lambda x: x[1])
        nearest_line, distance = valid_resistances[0]
        distance_pct = self._calculate_distance_pct(current_price, nearest_line.current_price)
        
        return (nearest_line, distance, distance_pct)
    
    def get_line_with_metrics(self, line_id: str) -> Optional[dict]:
        """
        Get a specific line with runtime-calculated metrics.
        
        Args:
            line_id: The ID of the line to retrieve
        
        Returns:
            Dictionary with line data plus computed metrics (distance, slope, duration)
        """
        for line in self._lines_cache:
            if line.line_id == line_id:
                return {
                    "line": line.model_dump(),
                    "metrics": {
                        "slope": self._calculate_slope(line),
                        "duration_minutes": self._calculate_duration(line),
                        "version_count": len(line.versions),
                        "price_range": {
                            "min": min(v.price for v in line.versions),
                            "max": max(v.price for v in line.versions)
                        }
                    }
                }
        return None
    
    def get_wave_with_metrics(self, wave_id: str) -> Optional[dict]:
        """
        Get a specific wave with member line details.
        
        Args:
            wave_id: The ID of the wave to retrieve
        
        Returns:
            Dictionary with wave data plus member line summaries
        """
        for wave in self._waves_cache:
            if wave.wave_id == wave_id:
                member_summaries = []
                for member_id in wave.members:
                    for line in self._lines_cache:
                        if line.line_id == member_id:
                            member_summaries.append({
                                "line_id": line.line_id,
                                "type": line.type,
                                "current_price": line.current_price,
                                "strength": line.strength
                            })
                            break
                
                return {
                    "wave": wave.model_dump(),
                    "members": member_summaries,
                    "total_price_range": {
                        "min": min(m["current_price"] for m in member_summaries) if member_summaries else 0,
                        "max": max(m["current_price"] for m in member_summaries) if member_summaries else 0
                    }
                }
        return None
    
    def get_active_trend(self) -> Optional[str]:
        """
        Determine the current active trend based on the most recent lines.
        
        Returns:
            "UPTREND", "DOWNTREND", "SIDEWAY", or None
        """
        if not self._lines_cache:
            return None
        
        # Sort by latest version time
        sorted_lines = sorted(
            self._lines_cache, 
            key=lambda x: x.versions[-1].time_wib if x.versions else datetime.min
        )
        
        if len(sorted_lines) < 2:
            return None
        
        last_two = sorted_lines[-2:]
        types = [l.type for l in last_two]
        
        if types == ["SUPPORT", "SUPPORT"]:
            # Check if prices are rising
            if last_two[1].current_price > last_two[0].current_price:
                return "UPTREND"
        elif types == ["RESISTANCE", "RESISTANCE"]:
            # Check if prices are falling
            if last_two[1].current_price < last_two[0].current_price:
                return "DOWNTREND"
        elif types != [types[0], types[0]]:
            return "SIDEWAY"
        
        return "CONSOLIDATION"
