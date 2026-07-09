"""
ACADEMY MODULE (The Brains - Statistical Analyst)

Tanggung Jawab:
1. Membaca storage/trading_cases.json (History Trading).
2. Mengelompokkan kasus berdasarkan worker_name dan wave_context (Market Regime).
3. Menghitung metrik performa per Worker per Regime:
   - Win Rate
   - Profit Factor
   - Average PnL
   - Total Trades
4. Menyimpan hasil ke storage/academy_knowledge.json.

GUARDRAILS:
- DILARANG menggunakan Pandas, Scikit-Learn, atau SQLite.
- Hanya Python standard library (json, collections, statistics).
- Proses BATCH (Offline), tidak memblokir pipeline live.
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Any, Optional
from datetime import datetime
from statistics import mean

class Academy:
    def __init__(self, storage_path: str = "storage"):
        self.storage_path = storage_path
        self.cases_file = os.path.join(storage_path, "trading_cases.json")
        self.knowledge_file = os.path.join(storage_path, "academy_knowledge.json")
        
        # Pastikan folder storage ada
        os.makedirs(storage_path, exist_ok=True)

    def load_trading_cases(self) -> List[Dict[str, Any]]:
        """Membaca semua trading case dari JSON Data Lake."""
        if not os.path.exists(self.cases_file):
            print(f"[Academy] Warning: {self.cases_file} not found. Starting with empty history.")
            return []
        
        try:
            with open(self.cases_file, 'r') as f:
                data = json.load(f)
                # Handle jika file berisi dict dengan key 'cases' atau langsung list
                if isinstance(data, dict) and 'cases' in data:
                    return data['cases']
                elif isinstance(data, list):
                    return data
                else:
                    return []
        except json.JSONDecodeError:
            print(f"[Academy] Error: {self.cases_file} is not valid JSON.")
            return []

    def _calculate_metrics(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Menghitung metrik statistik dari sekumpulan kasus.
        Menggunakan Python standard library saja.
        """
        if not cases:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "average_pnl": 0.0,
                "total_pnl": 0.0
            }
        
        total_trades = len(cases)
        wins = sum(1 for c in cases if c.get('outcome') == 'WIN')
        losses = sum(1 for c in cases if c.get('outcome') == 'LOSS')
        
        # Hitung Win Rate
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
        
        # Hitung PnL
        pnls = [c.get('pnl_usd', 0.0) for c in cases]
        total_pnl = sum(pnls)
        average_pnl = mean(pnls) if pnls else 0.0
        
        # Hitung Profit Factor (Gross Profit / Gross Loss)
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0.0)
        # Handle infinity untuk JSON
        if profit_factor == float('inf'):
            profit_factor = 999.99  # Cap value for serialization

        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "average_pnl": round(average_pnl, 2),
            "total_pnl": round(total_pnl, 2)
        }

    def analyze(self) -> Dict[str, Any]:
        """
        Proses utama Academy:
        1. Load cases
        2. Group by (worker_name, wave_context)
        3. Calculate metrics
        4. Save to knowledge file
        """
        print("[Academy] Loading trading cases...")
        cases = self.load_trading_cases()
        
        if not cases:
            print("[Academy] No data to analyze.")
            # Simpan struktur kosong
            knowledge = {"generated_at": datetime.utcnow().isoformat(), "knowledge": {}}
            self._save_knowledge(knowledge)
            return knowledge

        # Grouping: Key = (worker_name, wave_context)
        groups = defaultdict(list)
        for case in cases:
            worker = case.get('worker_name', 'Unknown')
            regime = case.get('wave_context', 'UNKNOWN')
            groups[(worker, regime)].append(case)

        print(f"[Academy] Analyzing {len(groups)} unique (Worker, Regime) combinations...")

        knowledge_base = {}
        for (worker, regime), group_cases in groups.items():
            metrics = self._calculate_metrics(group_cases)
            
            key = f"{worker}__{regime}"
            knowledge_base[key] = {
                "worker_name": worker,
                "regime": regime,
                "metrics": metrics,
                "sample_size": len(group_cases),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Log singkat
            print(f"  - {worker} @ {regime}: WR={metrics['win_rate']}%, PF={metrics['profit_factor']}, AvgPnL=${metrics['average_pnl']}")

        result = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_cases_analyzed": len(cases),
            "knowledge": knowledge_base
        }

        self._save_knowledge(result)
        print(f"[Academy] Knowledge saved to {self.knowledge_file}")
        return result

    def _save_knowledge(self, knowledge: Dict[str, Any]) -> None:
        """Menyimpan hasil analisis ke JSON."""
        with open(self.knowledge_file, 'w') as f:
            json.dump(knowledge, f, indent=2)

    def get_knowledge_for_worker(self, worker_name: str, regime: str) -> Optional[Dict[str, Any]]:
        """Mengambil pengetahuan spesifik untuk worker & regime tertentu."""
        if not os.path.exists(self.knowledge_file):
            return None
        
        with open(self.knowledge_file, 'r') as f:
            data = json.load(f)
        
        key = f"{worker_name}__{regime}"
        return data.get('knowledge', {}).get(key)


# AUDIT CHECKLIST: Academy
# [✓] Tidak menggunakan Pandas, Scikit-Learn, atau SQLite.
# [✓] Hanya menggunakan json, collections, statistics (standard library).
# [✓] Proses batch: membaca file, memproses, menulis file. Tidak ada blocking call network.
# [✓] Metrik dihitung secara deterministik berdasarkan data historis.
# [✓] Output terstruktur dalam JSON (academy_knowledge.json).
