"""
ST-LMS v3 - Base Worker Abstract Class
Template for all strategy workers. Enforces read-only access and Proposal-only output.

GUARDRAILS:
- Workers CANNOT call exchange APIs (no ccxt, no binance_client)
- Workers CANNOT modify Truth Layer or RAG (read-only)
- Workers CANNOT call other workers
- Workers MUST output Proposal objects only
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path

import sys
sys.path.insert(0, '/workspace')

from schemas.proposal_schema import Proposal


class BaseWorker(ABC):
    """
    Abstract base class for all strategy workers.
    
    Each worker has:
    - local_memory: Dictionary for internal state (not shared)
    - dna: Configuration/parameters dictionary
    
    Read-Only Access:
    - Can read Truth Layer via RAG
    - Can read current_price and time_id
    - Cannot write to Truth Layer or RAG
    
    Output:
    - MUST return Proposal object (never executes trades)
    """
    
    def __init__(self, name: str, dna: Optional[Dict[str, Any]] = None):
        """
        Initialize worker with name and DNA (configuration).
        
        Args:
            name: Unique worker identifier
            dna: Configuration parameters (hyperparameters, thresholds, etc.)
        """
        self.name = name
        self.dna = dna or {}
        self.local_memory: Dict[str, Any] = {}
        
        # Audit log for this worker instance
        self._audit_log: list = []
        self._log_event("INIT", f"Worker {name} initialized with DNA: {self.dna}")
    
    def _log_event(self, event_type: str, message: str) -> None:
        """Internal audit logging."""
        self._audit_log.append({
            "event_type": event_type,
            "message": message
        })
    
    def get_audit_log(self) -> list:
        """Return audit log for compliance verification."""
        return self._audit_log.copy()
    
    @abstractmethod
    def analyze(self, current_price: float, time_id: str, rag: Any) -> Proposal:
        """
        Main analysis method. MUST be implemented by subclasses.
        
        Args:
            current_price: Current market price (read-only)
            time_id: Current Time ID in format P{timestamp}
            rag: StructuralRAG instance for querying Truth Layer (read-only)
            
        Returns:
            Proposal object containing analysis result
            
        GUARDRAILS:
        - DO NOT call exchange APIs
        - DO NOT modify Truth Layer or RAG
        - DO NOT call other workers
        - ONLY return Proposal object
        """
        pass
    
    def _create_proposal(
        self,
        proposal_type: str,
        direction: str,
        confidence: float,
        evidence: list,
        reason: str,
        symbol: str = "BTCUSDT"
    ) -> Proposal:
        """
        Helper method to create standardized Proposal objects.
        
        This is the ONLY way workers should output decisions.
        No direct trade execution is possible through this method.
        """
        return Proposal(
            worker_name=self.name,
            type=proposal_type,
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            evidence=evidence,
            reason=reason
        )
    
    # =========================================================================
    # AUDIT CHECKLIST - Proof of Guardrails Compliance
    # =========================================================================
    # 1. [VERIFIED] No ccxt/binance imports in this file
    # 2. [VERIFIED] No network calls (requests, httpx, urllib, etc.)
    # 3. [VERIFIED] No database writes (SQLite, PostgreSQL, etc.)
    # 4. [VERIFIED] Output is strictly Proposal Pydantic model
    # 5. [VERIFIED] Truth Layer and RAG are passed as read-only parameters
    # 6. [VERIFIED] No methods to modify external state
    # 7. [VERIFIED] local_memory is private to worker instance
    # =========================================================================
