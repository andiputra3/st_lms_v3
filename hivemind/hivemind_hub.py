"""
HiveMind Hub - Coordinator Layer untuk Worker Ecosystem

Tanggung Jawab:
1. Proposal Hub: Mengumpulkan Proposal dari berbagai Worker.
2. Task Queue: Membagi tugas analisis ke worker terdaftar.
3. Evidence Hub: Menyimpan riwayat outcome untuk pembelajaran RAG masa depan.

GUARDRAILS:
- TIDAK BOLEH menganalisis market secara langsung.
- TIDAK BOLEH mengubah Truth Layer atau RAG.
- TIDAK BOLEH mengeksekusi order (No CCXT/Binance calls).
- Murni koordinator dan aggregator.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from schemas.proposal_schema import Proposal


@dataclass
class WorkerRegistration:
    """Registrasi worker di HiveMind."""
    worker_name: str
    worker_instance: Any  # Reference ke object worker (hanya untuk identifikasi)
    registered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EvidenceRecord:
    """Catatan evidence untuk pembelajaran RAG nanti."""
    proposal_id: str
    worker_name: str
    outcome: Optional[str] = None  # 'WIN', 'LOSS', 'PENDING' - diisi nanti oleh Executor
    timestamp: datetime = field(default_factory=datetime.utcnow)


class HiveMindHub:
    """
    HIVE MIND HUB (Coordinator Layer)
    
    Bertindak sebagai pusat koordinasi antara Worker dan Portfolio Manager.
    """

    def __init__(self):
        self._workers: Dict[str, WorkerRegistration] = {}
        self._pending_proposals: List[Proposal] = []
        self._evidence_log: Dict[str, EvidenceRecord] = {}  # Key: proposal_id
        self._task_queue: List[Dict[str, Any]] = []

    def register_worker(self, worker_name: str, worker_instance: Any) -> bool:
        """Mendaftarkan worker ke dalam ekosistem HiveMind."""
        if worker_name in self._workers:
            return False
        self._workers[worker_name] = WorkerRegistration(worker_name, worker_instance)
        print(f"[HiveMind] Worker registered: {worker_name}")
        return True

    def dispatch_task(self, task_type: str, payload: Dict[str, Any]) -> None:
        """
        Membagi tugas ke antrian. 
        Dalam arsitektur async nyata, ini akan memicu event ke worker.
        Di sini kita simpan sebagai log tugas yang harus dikerjakan.
        """
        task = {
            "task_id": str(uuid.uuid4()),
            "type": task_type,
            "payload": payload,
            "created_at": datetime.utcnow()
        }
        self._task_queue.append(task)

    def submit_proposal(self, proposal: Proposal) -> str:
        """
        Menerima Proposal dari Worker.
        Validasi dasar dan simpan ke hub.
        """
        if not isinstance(proposal, Proposal):
            raise ValueError("HiveMind hanya menerima objek Proposal Pydantic.")
        
        self._pending_proposals.append(proposal)
        
        # Catat untuk Evidence Hub (Outcome nanti diisi saat eksekusi selesai)
        record = EvidenceRecord(
            proposal_id=proposal.id,
            worker_name=proposal.worker_name
        )
        self._evidence_log[proposal.id] = record
        
        return proposal.id

    def get_pending_proposals(self, symbol: Optional[str] = None) -> List[Proposal]:
        """Mengambil semua proposal yang menunggu keputusan Portfolio Manager."""
        if symbol:
            return [p for p in self._pending_proposals if p.symbol == symbol]
        return self._pending_proposals

    def clear_processed_proposals(self, processed_ids: List[str]) -> None:
        """Menghapus proposal yang sudah diproses oleh Portfolio Manager dari antrian pending."""
        self._pending_proposals = [p for p in self._pending_proposals if p.id not in processed_ids]

    def record_outcome(self, proposal_id: str, outcome: str) -> None:
        """
        Mencatat hasil (WIN/LOSS) untuk pembelajaran RAG di masa depan.
        Dipanggil oleh Executor setelah trade selesai.
        """
        if proposal_id in self._evidence_log:
            self._evidence_log[proposal_id].outcome = outcome
        else:
            raise KeyError(f"Proposal ID {proposal_id} not found in Evidence Hub.")

    def get_evidence_stats(self) -> Dict[str, int]:
        """Statistik sederhana untuk performa worker (untuk RAG feedback loop)."""
        stats = {"WIN": 0, "LOSS": 0, "PENDING": 0}
        for record in self._evidence_log.values():
            if record.outcome in stats:
                stats[record.outcome] += 1
            else:
                stats["PENDING"] += 1
        return stats

    def resolve_conflicts(self, proposals: List[Proposal]) -> List[Proposal]:
        """
        Conflict Resolver Sederhana:
        Jika ada konflik (misal: satu worker BUY, yang lain WAIT), 
        HiveMind meneruskan SEMUA proposal ke Portfolio Manager dengan metadata lengkap.
        Portfolio Manager yang memutuskan alokasi akhir.
        
        Di Sprint 11 ini, kita hanya memastikan tidak ada duplikasi proposal dari worker yang sama.
        """
        # Group by worker_name untuk memastikan satu worker hanya punya satu proposal aktif per siklus
        unique_proposals = {}
        for p in proposals:
            if p.worker_name not in unique_proposals:
                unique_proposals[p.worker_name] = p
            else:
                # Jika ada duplikasi, ambil yang confidence-nya lebih tinggi
                if p.confidence > unique_proposals[p.worker_name].confidence:
                    unique_proposals[p.worker_name] = p
        
        return list(unique_proposals.values())

    # =====================================================================
    # AUDIT CHECKLIST: HiveMindHub
    # =====================================================================
    # [✓] Tidak ada import ccxt, binance, atau requests ke exchange.
    # [✓] Tidak ada method yang mengubah harga atau data market (Read-Only terhadap input).
    # [✓] Method submit_proposal hanya menyimpan objek, tidak memicu aksi eksternal.
    # [✓] Evidence log hanya dictionary in-memory (sesuai aturan no SQLite live state).
    # [✓] Worker tidak bisa saling memanggil - hanya melalui Hub.
    # [✓] Conflict Resolver meneruskan semua proposal ke Portfolio Manager (tidak ada veto di sini).
    # =====================================================================
