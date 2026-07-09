"""
ST-LMS v3 - Wave Builder Engine
Groups SupertrendLines into SupertrendWaves based on pattern detection.
Pattern rules:
- SUPPORT-SUPPORT-SUPPORT (rising) = UPTREND_LADDER
- RESISTANCE-RESISTANCE-RESISTANCE (falling) = DOWNTREND_LADDER
- SUPPORT-RESISTANCE-SUPPORT-RESISTANCE = SIDEWAY_CHANNEL
- Single line = TREND_START
"""
from typing import List, Optional
import hashlib
import sys
sys.path.insert(0, '/workspace')

from truth_layer.schemas import SupertrendLine, SupertrendWave


class WaveBuilder:
    """
    Builds SupertrendWaves from a stream of SupertrendLines.
    Detects market structure patterns based on line sequence.
    """
    
    def __init__(self, min_lines_for_wave: int = 2):
        """
        Initialize Wave Builder.
        
        Args:
            min_lines_for_wave: Minimum number of lines to form a wave
        """
        self.min_lines_for_wave = min_lines_for_wave
        self.lines_buffer: List[SupertrendLine] = []
        self.completed_waves: List[SupertrendWave] = []
        self.wave_counter: int = 0
    
    def _generate_wave_id(self, time_id: str) -> str:
        """
        Generate unique wave ID: W{YYMMDDHHmm}-{counter}
        Format: W2607081921-001 (not WP...)
        """
        self.wave_counter += 1
        # Extract YYMMDDHHmm from point_id (e.g., P2607081921 -> 2607081921)
        # Point ID format: P{YYMMDDHHmm}
        if time_id.startswith('P'):
            time_suffix = time_id[1:]  # Remove 'P' prefix
        else:
            time_suffix = time_id
        return f"W{time_suffix}-{self.wave_counter:03d}"
    
    def _generate_signature(self, lines: List[SupertrendLine]) -> str:
        """
        Generate a hash-like signature representing the wave structure.
        Format: TYPE-TYPE-TYPE-price1-price2-price3
        """
        type_sequence = "-".join([line.type[:3] for line in lines])
        price_sequence = "-".join([str(int(line.current_price)) for line in lines])
        return f"{type_sequence}-{price_sequence}"
    
    def _detect_pattern(self, lines: List[SupertrendLine]) -> str:
        """
        Detect market pattern based on line sequence.
        
        Patterns:
        - UPTREND_LADDER: Consecutive SUPPORT lines with rising prices
        - DOWNTREND_LADDER: Consecutive RESISTANCE lines with falling prices
        - SIDEWAY_CHANNEL: Alternating SUPPORT and RESISTANCE
        - TREND_REVERSAL: Change from SUPPORT to RESISTANCE or vice versa
        - CONSOLIDATION: Same type lines at similar prices
        """
        if len(lines) < 2:
            return "SINGLE_LINE"
        
        types = [line.type for line in lines]
        prices = [line.current_price for line in lines]
        
        # Check for alternating pattern (Sideway)
        is_alternating = True
        for i in range(1, len(types)):
            if types[i] == types[i-1]:
                is_alternating = False
                break
        
        if is_alternating and len(lines) >= 3:
            return "SIDEWAY_CHANNEL"
        
        # Check for consecutive same-type lines (Trend Ladder)
        if all(t == "SUPPORT" for t in types):
            # Check if prices are rising (uptrend)
            if all(prices[i] >= prices[i-1] for i in range(1, len(prices))):
                return "UPTREND_LADDER"
            else:
                return "SUPPORT_CONSOLIDATION"
        
        if all(t == "RESISTANCE" for t in types):
            # Check if prices are falling (downtrend)
            if all(prices[i] <= prices[i-1] for i in range(1, len(prices))):
                return "DOWNTREND_LADDER"
            else:
                return "RESISTANCE_CONSOLIDATION"
        
        # Check for trend reversal
        if len(lines) >= 2 and types[0] != types[-1]:
            return "TREND_REVERSAL"
        
        # Default pattern
        return "MIXED_STRUCTURE"
    
    def process_lines(self, lines: List[SupertrendLine], force_complete: bool = False) -> List[SupertrendWave]:
        """
        Process a list of SupertrendLines and build waves.
        
        Args:
            lines: List of SupertrendLines to process
            force_complete: If True, force creation of wave even with minimal lines
        
        Returns:
            List of completed SupertrendWaves
        """
        # Add lines to buffer
        self.lines_buffer.extend(lines)
        
        # Sort lines by their first version timestamp
        self.lines_buffer.sort(key=lambda x: x.versions[0].time_wib)
        
        # Group lines into waves based on pattern changes
        waves = []
        current_wave_lines: List[SupertrendLine] = []
        
        for line in self.lines_buffer:
            if not current_wave_lines:
                current_wave_lines.append(line)
            else:
                # Check if adding this line would change the pattern significantly
                test_lines = current_wave_lines + [line]
                current_pattern = self._detect_pattern(current_wave_lines)
                new_pattern = self._detect_pattern(test_lines)
                
                # If pattern changes dramatically or we have enough lines, close current wave
                if (current_pattern != new_pattern and len(current_wave_lines) >= self.min_lines_for_wave) or \
                   (len(current_wave_lines) >= 5):  # Max wave size
                    # Create wave from current lines
                    wave = self._create_wave(current_wave_lines)
                    waves.append(wave)
                    current_wave_lines = [line]
                else:
                    current_wave_lines.append(line)
        
        # Handle remaining lines
        if current_wave_lines and (force_complete or len(current_wave_lines) >= self.min_lines_for_wave):
            wave = self._create_wave(current_wave_lines)
            waves.append(wave)
            # Remove processed lines from buffer
            self.lines_buffer = []
        elif current_wave_lines:
            # Keep remaining lines in buffer for next processing
            self.lines_buffer = current_wave_lines
        
        self.completed_waves.extend(waves)
        return waves
    
    def _create_wave(self, lines: List[SupertrendLine]) -> SupertrendWave:
        """
        Create a SupertrendWave from a list of lines.
        """
        if not lines:
            raise ValueError("Cannot create wave from empty line list")
        
        pattern = self._detect_pattern(lines)
        sequence = [line.type for line in lines]
        member_ids = [line.line_id for line in lines]
        signature = self._generate_signature(lines)
        
        # Determine dominant color (majority vote)
        green_count = sum(1 for line in lines if line.color == "GREEN")
        red_count = len(lines) - green_count
        dominant_color = "GREEN" if green_count >= red_count else "RED"
        
        # Use timestamp from first line's first version
        first_time_id = lines[0].versions[0].point_id
        
        wave_id = self._generate_wave_id(first_time_id)
        
        return SupertrendWave(
            wave_id=wave_id,
            pattern=pattern,
            sequence=sequence,
            members=member_ids,
            signature=signature,
            color=dominant_color
        )
    
    def get_all_waves(self) -> List[SupertrendWave]:
        """
        Get all completed waves.
        """
        return self.completed_waves.copy()
    
    def reset(self) -> None:
        """
        Reset the builder state.
        """
        self.lines_buffer = []
        self.completed_waves = []
        self.wave_counter = 0
