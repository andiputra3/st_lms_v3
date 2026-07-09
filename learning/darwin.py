"""
DARWIN MODULE (Capital Allocator - Decision Maker)

Tanggung Jawab:
1. Membaca academy_knowledge.json (hasil analisis Academy).
2. Memperbarui Leaderboard (storage/worker_scores.json).
3. Logika Alokasi Modal:
   - Jika Win Rate < 40% ATAU Profit Factor < 1.0 -> Status REPLAY_ONLY.
   - Jika performa baik -> Status LIVE + confidence_multiplier.
4. Menghasilkan JSON worker_scores.json berisi:
   - worker_name, regime, score, status (LIVE/REPLAY_ONLY), capital_weight.

GUARDRAILS:
- DILARANG menggunakan Pandas, Scikit-Learn, atau SQLite.
- Proses BATCH (Offline/Evaluatif).
- Output HARUS berupa JSON yang bisa dibaca Portfolio Manager.
- Keputusan berdasarkan bukti statistik, BUKAN hardcode.
"""

import json
import os
from typing import Dict, List, Any
from datetime import datetime

class Darwin:
    def __init__(self, storage_path: str = "storage"):
        self.storage_path = storage_path
        self.knowledge_file = os.path.join(storage_path, "academy_knowledge.json")
        self.scores_file = os.path.join(storage_path, "worker_scores.json")
        
        # Thresholds (Bisa dikonfigurasi)
        self.min_win_rate = 40.0  # %
        self.min_profit_factor = 1.0
        
        # Pastikan folder storage ada
        os.makedirs(storage_path, exist_ok=True)

    def load_knowledge(self) -> Dict[str, Any]:
        """Membaca hasil analisis dari Academy."""
        if not os.path.exists(self.knowledge_file):
            print(f"[Darwin] Warning: {self.knowledge_file} not found. Run Academy first.")
            return {}
        
        with open(self.knowledge_file, 'r') as f:
            return json.load(f)

    def _calculate_score(self, metrics: Dict[str, Any]) -> float:
        """
        Menghitung skor kombinasidari metrik.
        Formula sederhana: (WinRate * 0.4) + (ProfitFactor * 10 * 0.4) + (AvgPnL normalized * 0.2)
        Ini bisa dioptimalkan nanti dengan machine learning.
        """
        win_rate = metrics.get('win_rate', 0.0)
        profit_factor = metrics.get('profit_factor', 0.0)
        avg_pnl = metrics.get('average_pnl', 0.0)
        
        # Normalisasi AvgPnL (asumsi range -50 sampai +50 untuk contoh)
        # Clamp value agar tidak outlier
        pnl_normalized = max(-50, min(50, avg_pnl)) / 50.0  # Range -1.0 to 1.0
        
        # Score calculation
        # WinRate contribution (max 40 points)
        wr_score = (win_rate / 100.0) * 40.0
        
        # Profit Factor contribution (max 40 points, cap PF at 5.0 for scaling)
        pf_capped = min(profit_factor, 5.0)
        pf_score = (pf_capped / 5.0) * 40.0
        
        # PnL contribution (max 20 points)
        pnl_score = (pnl_normalized + 1.0) * 10.0  # Shift -1..1 to 0..2, then *10
        
        total_score = wr_score + pf_score + pnl_score
        return round(total_score, 2)

    def _determine_status_and_multiplier(self, metrics: Dict[str, Any]) -> tuple:
        """
        Menentukan status (LIVE/REPLAY_ONLY) dan confidence_multiplier.
        Berdasarkan aturan ketat:
        - WR < 40% OR PF < 1.0 -> REPLAY_ONLY, multiplier 0.5
        - ELSE -> LIVE, multiplier 1.0 + bonus
        """
        win_rate = metrics.get('win_rate', 0.0)
        profit_factor = metrics.get('profit_factor', 0.0)
        
        if win_rate < self.min_win_rate or profit_factor < self.min_profit_factor:
            # Gagal standar minimum
            status = "REPLAY_ONLY"
            multiplier = 0.5  # Kurangi confidence proposal jadi setengah
            capital_weight = 0.0  # Tidak dapat alokasi modal LIVE
        else:
            # Lolos standar minimum
            status = "LIVE"
            
            # Bonus multiplier berdasarkan performa di atas threshold
            # Semakin tinggi PF dan WR, semakin besar bonus (max 1.5x)
            wr_bonus = min((win_rate - self.min_win_rate) / 100.0, 0.25)  # Max +0.25
            pf_bonus = min((profit_factor - self.min_profit_factor) / 5.0, 0.25)  # Max +0.25
            
            base_multiplier = 1.0
            multiplier = round(base_multiplier + wr_bonus + pf_bonus, 2)
            multiplier = min(multiplier, 1.5)  # Cap di 1.5x
            
            # Capital weight: proporsional dengan score relatif
            # Akan dinormalisasi nanti di level leaderboard global
            capital_weight = round((win_rate / 100.0) * (profit_factor / (profit_factor + 1.0)), 2)

        return status, multiplier, capital_weight

    def evaluate(self) -> Dict[str, Any]:
        """
        Proses utama Darwin:
        1. Load knowledge dari Academy
        2. Hitung score, status, multiplier untuk setiap (Worker, Regime)
        3. Simpan ke worker_scores.json (Leaderboard)
        """
        print("[Darwin] Loading academy knowledge...")
        knowledge_data = self.load_knowledge()
        
        if not knowledge_data:
            print("[Darwin] No knowledge to evaluate.")
            result = {
                "generated_at": datetime.utcnow().isoformat(),
                "leaderboard": []
            }
            self._save_scores(result)
            return result

        knowledge_base = knowledge_data.get('knowledge', {})
        leaderboard = []

        print(f"[Darwin] Evaluating {len(knowledge_base)} entries...")

        for key, entry in knowledge_base.items():
            worker_name = entry.get('worker_name', 'Unknown')
            regime = entry.get('regime', 'UNKNOWN')
            metrics = entry.get('metrics', {})
            
            # Hitung score
            score = self._calculate_score(metrics)
            
            # Tentukan status & multiplier
            status, multiplier, capital_weight = self._determine_status_and_multiplier(metrics)
            
            record = {
                "worker_name": worker_name,
                "regime": regime,
                "score": score,
                "status": status,
                "confidence_multiplier": multiplier,
                "capital_weight": capital_weight,
                "metrics_summary": {
                    "win_rate": metrics.get('win_rate'),
                    "profit_factor": metrics.get('profit_factor'),
                    "total_trades": metrics.get('total_trades')
                },
                "evaluated_at": datetime.utcnow().isoformat()
            }
            
            leaderboard.append(record)
            
            # Log evaluasi
            icon = "✅" if status == "LIVE" else "🚫"
            print(f"  {icon} {worker_name} @ {regime}: Score={score}, Status={status}, Mult={multiplier}x")

        # Sort leaderboard by score descending
        leaderboard.sort(key=lambda x: x['score'], reverse=True)

        result = {
            "generated_at": datetime.utcnow().isoformat(),
            "thresholds_used": {
                "min_win_rate": self.min_win_rate,
                "min_profit_factor": self.min_profit_factor
            },
            "leaderboard": leaderboard
        }

        self._save_scores(result)
        print(f"[Darwin] Leaderboard saved to {self.scores_file}")
        return result

    def _save_scores(self, scores: Dict[str, Any]) -> None:
        """Menyimpan leaderboard ke JSON."""
        with open(self.scores_file, 'w') as f:
            json.dump(scores, f, indent=2)

    def get_worker_config(self, worker_name: str, regime: str) -> Dict[str, Any]:
        """
        Mengambil konfigurasi untuk worker tertentu.
        Digunakan oleh Portfolio Manager untuk menentukan alokasi.
        """
        if not os.path.exists(self.scores_file):
            return {
                "status": "UNKNOWN",
                "confidence_multiplier": 1.0,
                "capital_weight": 0.0
            }
        
        with open(self.scores_file, 'r') as f:
            data = json.load(f)
        
        for entry in data.get('leaderboard', []):
            if entry['worker_name'] == worker_name and entry['regime'] == regime:
                return {
                    "status": entry['status'],
                    "confidence_multiplier": entry['confidence_multiplier'],
                    "capital_weight": entry['capital_weight'],
                    "score": entry['score']
                }
        
        # Default jika tidak ditemukan
        return {
            "status": "REPLAY_ONLY",  # Safety default
            "confidence_multiplier": 1.0,
            "capital_weight": 0.0,
            "score": 0.0
        }


# AUDIT CHECKLIST: Darwin
# [✓] Tidak menggunakan Pandas, Scikit-Learn, atau SQLite.
# [✓] Hanya menggunakan json, os, datetime (standard library).
# [✓] Proses batch: membaca file knowledge, memproses, menulis leaderboard.
# [✓] Status REPLAY_ONLY/LIVE ditentukan oleh metrik statistik (WR, PF), BUKAN hardcode.
# [✓] Confidence multiplier dihitung berdasarkan performa di atas threshold.
# [✓] Output JSON (worker_scores.json) siap dikonsumsi oleh Portfolio Manager.
# [✓] Safety default: Worker baru/tidak dikenal -> REPLAY_ONLY.
