"""
AUDIT DASHBOARD - Truth Validation Platform (Sprint 12)

READ-ONLY: Alat untuk mengaudit jejak keputusan tanpa mengubah state.
Tidak memanggil exchange, tidak memodifikasi data.
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path


class AuditDashboard:
    """
    Dashboard READ-ONLY untuk memverifikasi "Pipeline Truth".
    Menampilkan jejak lengkap dari Truth Layer hingga Exit Decision.
    """

    def __init__(self, storage_path: str = "storage"):
        self.storage_path = Path(storage_path)
        
        # File paths
        self.truth_layer_path = self.storage_path / "truth_layer.json"
        self.rag_index_path = self.storage_path / "rag_index.json"
        self.proposals_path = self.storage_path / "proposals_log.json"
        self.intents_path = self.storage_path / "execution_intents.json"
        self.positions_path = self.storage_path / "positions_log.json"
        self.trading_cases_path = self.storage_path / "trading_cases.json"

    def _read_json(self, filepath: Path) -> List[Dict]:
        """Membaca file JSON dengan aman."""
        if not filepath.exists():
            return []
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else [data]
        except (json.JSONDecodeError, IOError):
            return []

    def _format_border(self, title: str, width: int = 80) -> str:
        """Membuat border formatting untuk CLI."""
        line = "=" * width
        return f"\n{line}\n{title.center(width)}\n{line}"

    def _format_section(self, section_name: str, content: str) -> str:
        """Format section dengan indentasi."""
        return f"\n[{section_name}]\n{content}"

    def generate_audit_report(self, time_id: str) -> str:
        """
        Generate laporan audit terstruktur untuk Time ID tertentu.
        
        Args:
            time_id: Time ID (WIB) yang ingin diaudit
            
        Returns:
            String laporan terformat untuk CLI
        """
        report_lines = []
        report_lines.append(self._format_border(f"AUDIT REPORT - Time ID: {time_id}"))

        # =========================================================================
        # [1] TRUTH LAYER AUDIT
        # =========================================================================
        report_lines.append(self._format_section("TRUTH LAYER", "-" * 40))
        
        truth_data = self._read_json(self.truth_layer_path)
        truth_at_time = [t for t in truth_data if t.get('time_id') == time_id]
        
        if truth_at_time:
            latest_truth = truth_at_time[-1]
            report_lines.append(f"  • Active Lines: {len(latest_truth.get('active_lines', []))}")
            for line in latest_truth.get('active_lines', [])[:5]:  # Max 5 lines
                line_type = line.get('type', 'UNKNOWN')
                price = line.get('price', 0)
                strength = line.get('strength', 'N/A')
                report_lines.append(f"    - {line_type}: {price} (Strength: {strength})")
            
            wave = latest_truth.get('current_wave', 'UNKNOWN')
            report_lines.append(f"  • Current Wave: {wave}")
            
            current_price = latest_truth.get('current_price', 0)
            report_lines.append(f"  • Current Price: {current_price}")
        else:
            report_lines.append("  ⚠ No Truth Layer data found for this time_id")

        # =========================================================================
        # [2] RAG FACT CARDS AUDIT
        # =========================================================================
        report_lines.append(self._format_section("RAG FACT CARDS", "-" * 40))
        
        rag_data = self._read_json(self.rag_index_path)
        rag_at_time = [r for r in rag_data if r.get('time_id') == time_id]
        
        if rag_at_time:
            latest_rag = rag_at_time[-1]
            fact_cards = latest_rag.get('fact_cards', [])
            report_lines.append(f"  • Total Fact Cards Retrieved: {len(fact_cards)}")
            for i, card in enumerate(fact_cards[:5], 1):  # Max 5 cards
                source = card.get('source', 'Unknown')
                fact = card.get('fact', '')[:60] + "..." if len(card.get('fact', '')) > 60 else card.get('fact', '')
                confidence = card.get('confidence', 0)
                report_lines.append(f"    {i}. [{source}] {fact} (Conf: {confidence})")
        else:
            report_lines.append("  ⚠ No RAG data found for this time_id")

        # =========================================================================
        # [3] HIVEMIND PROPOSALS AUDIT
        # =========================================================================
        report_lines.append(self._format_section("HIVEMIND PROPOSALS", "-" * 40))
        
        proposals_data = self._read_json(self.proposals_path)
        proposals_at_time = [p for p in proposals_data if p.get('time_id') == time_id]
        
        if proposals_at_time:
            report_lines.append(f"  • Total Proposals: {len(proposals_at_time)}")
            for prop in proposals_at_time:
                worker = prop.get('worker_name', 'Unknown')
                ptype = prop.get('type', 'WAIT')
                direction = prop.get('direction', 'NEUTRAL')
                confidence = prop.get('confidence', 0)
                reason = prop.get('reason', '')[:50] + "..." if len(prop.get('reason', '')) > 50 else prop.get('reason', '')
                report_lines.append(f"    • {worker}: {ptype} {direction} (Conf: {confidence})")
                report_lines.append(f"      Reason: {reason}")
        else:
            report_lines.append("  ⚠ No proposals found for this time_id")

        # =========================================================================
        # [4] PORTFOLIO ALLOCATION AUDIT
        # =========================================================================
        report_lines.append(self._format_section("PORTFOLIO ALLOCATION", "-" * 40))
        
        intents_data = self._read_json(self.intents_path)
        intents_at_time = [i for i in intents_data if i.get('time_id') == time_id]
        
        if intents_at_time:
            report_lines.append(f"  • Total Intents Generated: {len(intents_at_time)}")
            for intent in intents_at_time:
                symbol = intent.get('symbol', 'N/A')
                direction = intent.get('direction', 'N/A')
                mode = intent.get('mode', 'N/A')
                size = intent.get('size_usd', 0)
                worker = intent.get('worker_name', 'N/A')
                status_icon = "🟢 LIVE" if mode == "LIVE" else "🟡 REPLAY"
                report_lines.append(f"    {status_icon} | {symbol} {direction} | Worker: {worker} | Size: ${size}")
        else:
            report_lines.append("  ⚠ No execution intents found for this time_id")

        # =========================================================================
        # [5] EXIT MANAGER AUDIT
        # =========================================================================
        report_lines.append(self._format_section("EXIT MANAGER STATUS", "-" * 40))
        
        # Cek positions log
        positions_data = self._read_json(self.positions_path)
        active_positions = [p for p in positions_data if p.get('entry_time_id') and p.get('exit_time_id') is None]
        
        report_lines.append(f"  • Active Positions Before This Candle: {len(active_positions)}")
        for pos in active_positions:
            symbol = pos.get('symbol', 'N/A')
            direction = pos.get('direction', 'N/A')
            entry_price = pos.get('entry_price', 0)
            pnl = pos.get('unrealized_pnl', 0)
            worker = pos.get('worker_name', 'N/A')
            report_lines.append(f"    - {symbol} {direction} | Entry: {entry_price} | PnL: ${pnl:.2f} | Worker: {worker}")
        
        # Cek trading cases untuk exit yang terjadi pada time_id ini
        cases_data = self._read_json(self.trading_cases_path)
        exits_at_time = [c for c in cases_data if c.get('exit_time_id') == time_id]
        
        if exits_at_time:
            report_lines.append(f"\n  🚨 EXITS EXECUTED AT THIS TIME: {len(exits_at_time)}")
            for case in exits_at_time:
                symbol = case.get('symbol', 'N/A')
                pnl = case.get('pnl', 0)
                exit_reason = case.get('exit_reason', 'Unknown')
                worker = case.get('worker_name', 'N/A')
                icon = "💰" if pnl > 0 else "📉"
                report_lines.append(f"    {icon} {symbol} | PnL: ${pnl:.2f} | Reason: {exit_reason} | Worker: {worker}")
        else:
            report_lines.append("  ✓ No exits executed at this time_id")

        # =========================================================================
        # SUMMARY
        # =========================================================================
        report_lines.append(self._format_border("END OF AUDIT REPORT"))
        
        return "\n".join(report_lines)

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Mendapatkan ringkasan statistik dari seluruh data historis.
        """
        cases_data = self._read_json(self.trading_cases_path)
        
        if not cases_data:
            return {"error": "No trading cases found"}
        
        total_cases = len(cases_data)
        wins = sum(1 for c in cases_data if c.get('outcome') == 'WIN')
        losses = sum(1 for c in cases_data if c.get('outcome') == 'LOSS')
        total_pnl = sum(c.get('pnl', 0) for c in cases_data)
        
        win_rate = (wins / total_cases * 100) if total_cases > 0 else 0
        
        # Group by worker
        worker_stats = {}
        for case in cases_data:
            worker = case.get('worker_name', 'Unknown')
            if worker not in worker_stats:
                worker_stats[worker] = {'wins': 0, 'losses': 0, 'pnl': 0, 'count': 0}
            worker_stats[worker]['count'] += 1
            worker_stats[worker]['pnl'] += case.get('pnl', 0)
            if case.get('outcome') == 'WIN':
                worker_stats[worker]['wins'] += 1
            elif case.get('outcome') == 'LOSS':
                worker_stats[worker]['losses'] += 1
        
        return {
            "total_cases": total_cases,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "worker_performance": worker_stats
        }

# AUDIT CHECKLIST: AuditDashboard
# [✓] READ-ONLY: Tidak ada method yang mengubah file atau state
# [✓] No Exchange Calls: Tidak ada import ccxt, binance, atau requests ke exchange
# [✓] Deterministic: Tidak menggunakan datetime.now() atau utcnow()
# [✓] Structured Output: Laporan terformat dengan section jelas (Truth, RAG, HiveMind, Portfolio, Exit)
# [✓] Human Readable: Formatting CLI dengan border dan indentasi rapi
# [✓] Complete Trail: Menampilkan jejak dari awal (Truth) hingga akhir (Exit/TradingCase)
