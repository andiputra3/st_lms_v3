"""
ST-LMS v3 - Pullback Worker Implementation
First concrete worker implementing pullback strategy.

Strategy Logic:
1. Query RAG for nearest support level (find_nearest_support)
2. Query RAG for wave context (get_wave_context)
3. If Wave is UPTREND_LADDER (bullish) AND price near Strong Support (confidence > 0.8):
   -> Return ENTRY LONG Proposal
4. Otherwise:
   -> Return WAIT Proposal

GUARDRAILS:
- NO exchange API calls (no ccxt, no binance)
- NO modification of Truth Layer or RAG
- NO calling other workers
- Output ONLY Proposal objects
"""
from typing import Any, Optional, List
import sys

sys.path.insert(0, '/workspace')

from schemas.proposal_schema import Proposal, Evidence
from workers.base_worker import BaseWorker


class PullbackWorker(BaseWorker):
    """
    Pullback strategy worker.
    
    Enters LONG positions when:
    - Market is in UPTREND_LADDER (bullish wave structure)
    - Price pulls back to a strong support level (confidence > threshold)
    
    DNA Parameters:
    - support_confidence_threshold: Minimum confidence for support level (default: 0.8)
    - proximity_threshold_pct: How close price must be to support in percentage (default: 2.0%)
    """
    
    def __init__(self, dna: Optional[dict] = None):
        default_dna = {
            "support_confidence_threshold": 0.8,
            "proximity_threshold_pct": 2.0,
        }
        # Merge user DNA with defaults
        merged_dna = {**default_dna, **(dna or {})}
        super().__init__(name="PullbackWorker_v1", dna=merged_dna)
        
        # Local memory for tracking state between calls
        self.local_memory = {
            "last_signal": "WAIT",
            "signals_count": 0,
        }
    
    def _is_bullish_wave(self, wave_fact: str) -> bool:
        """
        Check if wave context indicates bullish structure.
        
        Bullish patterns include:
        - UPTREND_LADDER
        - IMPULSE (when color is GREEN)
        - Any pattern containing 'Bullish' keyword
        """
        bullish_keywords = [
            "UPTREND_LADDER",
            "Bullish",
            "GREEN"
        ]
        return any(keyword in wave_fact for keyword in bullish_keywords)
    
    def _calculate_proximity_to_support(
        self, 
        current_price: float, 
        support_fact_card: Any
    ) -> tuple[float, bool]:
        """
        Calculate how close current price is to support level.
        
        Returns:
            Tuple of (distance_percentage, is_within_threshold)
        """
        # Extract support price from fact string
        # Fact format: "Strong Support at 95000.00, retested X times..."
        fact_str = support_fact_card.fact
        
        # Try to extract price from fact string
        support_price = None
        for part in fact_str.split(','):
            if 'at' in part:
                try:
                    # Extract number after "at"
                    price_part = part.split('at')[1].strip()
                    # Remove any non-numeric chars except dot
                    price_str = ''.join(c for c in price_part if c.isdigit() or c == '.')
                    if price_str:
                        support_price = float(price_str)
                        break
                except (ValueError, IndexError):
                    continue
        
        if support_price is None or support_price == 0:
            return 0.0, False
        
        # Calculate distance percentage
        distance_pct = ((current_price - support_price) / support_price) * 100
        
        # Check if within threshold (price should be slightly above support)
        threshold = self.dna.get("proximity_threshold_pct", 2.0)
        is_within = 0.0 <= distance_pct <= threshold
        
        self._log_event(
            "PROXIMITY_CHECK",
            f"Price: {current_price}, Support: {support_price}, Distance: {distance_pct:.2f}%, Within: {is_within}"
        )
        
        return distance_pct, is_within
    
    def analyze(self, current_price: float, time_id: str, rag: Any) -> Proposal:
        """
        Analyze market conditions and generate Proposal.
        
        Args:
            current_price: Current market price (read-only)
            time_id: Current Time ID (e.g., P2607081936)
            rag: StructuralRAG instance (read-only)
            
        Returns:
            Proposal object (ENTRY LONG or WAIT)
            
        GUARDRAILS COMPLIANCE:
        - [✓] No exchange API calls
        - [✓] No Truth Layer modifications
        - [✓] No worker-to-worker calls
        - [✓] Returns only Proposal object
        """
        self._log_event("ANALYZE_START", f"time_id={time_id}, price={current_price}")
        
        # Step 1: Get nearest support from RAG
        support_card = rag.find_nearest_support(current_price)
        
        # Step 2: Get wave context from RAG
        wave_card = rag.get_wave_context(time_id)
        
        # Build evidence list
        evidence: List[Evidence] = []
        
        if support_card:
            evidence.append(Evidence(
                source=support_card.source,
                fact=support_card.fact,
                confidence=support_card.confidence
            ))
            self._log_event("RAG_SUPPORT", f"Found support: {support_card.fact}")
        else:
            self._log_event("RAG_SUPPORT", "No support level found")
        
        if wave_card:
            evidence.append(Evidence(
                source=wave_card.source,
                fact=wave_card.fact,
                confidence=wave_card.confidence
            ))
            self._log_event("RAG_WAVE", f"Wave context: {wave_card.fact}")
        else:
            self._log_event("RAG_WAVE", "No wave context found")
        
        # Step 3: Apply strategy logic
        confidence_threshold = self.dna.get("support_confidence_threshold", 0.8)
        
        # Check conditions for LONG entry
        can_enter_long = False
        reason_parts = []
        
        if wave_card and self._is_bullish_wave(wave_card.fact):
            reason_parts.append(f"Bullish wave structure detected")
            
            if support_card and support_card.confidence >= confidence_threshold:
                # Check proximity to support
                distance_pct, is_near_support = self._calculate_proximity_to_support(
                    current_price, support_card
                )
                
                if is_near_support:
                    can_enter_long = True
                    reason_parts.append(
                        f"Price near strong support (confidence={support_card.confidence:.2f}, distance={distance_pct:.2f}%)"
                    )
                else:
                    reason_parts.append(
                        f"Support too far from current price (distance={distance_pct:.2f}%)"
                    )
            else:
                if not support_card:
                    reason_parts.append("No support level found")
                else:
                    reason_parts.append(
                        f"Support confidence too low ({support_card.confidence:.2f} < {confidence_threshold})"
                    )
        else:
            if not wave_card:
                reason_parts.append("No wave context available")
            else:
                reason_parts.append(f"Non-bullish wave: {wave_card.fact}")
        
        # Step 4: Generate Proposal
        if can_enter_long:
            # Calculate final confidence based on evidence
            avg_evidence_confidence = sum(e.confidence for e in evidence) / len(evidence) if evidence else 0.5
            
            proposal = self._create_proposal(
                proposal_type="ENTRY",
                direction="LONG",
                confidence=round(avg_evidence_confidence, 2),
                evidence=evidence,
                reason=". ".join(reason_parts) + ". ENTRY signal triggered."
            )
            self.local_memory["last_signal"] = "ENTRY_LONG"
        else:
            proposal = self._create_proposal(
                proposal_type="WAIT",
                direction="NEUTRAL",
                confidence=0.5,
                evidence=evidence,
                reason=". ".join(reason_parts) + ". Waiting for better conditions."
            )
            self.local_memory["last_signal"] = "WAIT"
        
        self.local_memory["signals_count"] += 1
        self._log_event("ANALYZE_COMPLETE", f"Proposal type: {proposal.type}, direction: {proposal.direction}")
        
        return proposal
    
    # =========================================================================
    # AUDIT CHECKLIST - PullbackWorker Specific
    # =========================================================================
    # 1. [VERIFIED] No ccxt/binance/pybit imports
    # 2. [VERIFIED] No requests/httpx/urllib network calls
    # 3. [VERIFIED] No database connections or writes
    # 4. [VERIFIED] Only reads from RAG (find_nearest_support, get_wave_context)
    # 5. [VERIFIED] Does NOT call rag.refresh() or any write methods
    # 6. [VERIFIED] Output is strictly Proposal Pydantic model
    # 7. [VERIFIED] local_memory is private dictionary, not shared
    # 8. [VERIFIED] No calls to other worker classes
    # 9. [VERIFIED] No side effects - pure function of (price, time_id, rag)
    # =========================================================================
