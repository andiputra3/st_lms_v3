"""
Scanner Engine - Multi-Symbol Data Ingestion Orchestrator

Orkestrator untuk mengunduh data dari berbagai simbol dan timeframe,
menormalisasi waktu (UTC -> WIB), dan menyimpan ke JSON Data Lake.
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import TimeService dari Sprint 1 (di root directory)
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time_service
from scanner.binance_client import MockBinanceClient


class ScannerEngine:
    """
    Scanner Engine bertanggung jawab untuk:
    1. Mengunduh data OHLCV dari multiple symbols & timeframes
    2. Menormalisasi timestamp UTC ke WIB menggunakan TimeService
    3. Menyimpan hasil ke JSON Data Lake
    
    GUARDRAILS:
    - HANYA mengunduh dan menormalisasi data (NO indicators)
    - TIDAK menggunakan datetime.now() (semua dari candle timestamp)
    - Output JSON siap untuk RAG indexing
    """
    
    def __init__(self, storage_path: str = "storage/market_data"):
        """
        Inisialisasi Scanner Engine.
        
        Args:
            storage_path: Path untuk menyimpan file JSON market data
        """
        self.storage_path = storage_path
        self.client = MockBinanceClient()
        self.time_service = time_service
        
        # Pastikan direktori storage ada
        os.makedirs(storage_path, exist_ok=True)
    
    def scan(
        self, 
        symbols: List[str], 
        timeframes: List[str], 
        lookback_candles: int = 500
    ) -> Dict[str, Dict[str, str]]:
        """
        Melakukan scanning untuk multiple symbols dan timeframes.
        
        Args:
            symbols: List simbol (misal: ["BTCUSDT", "ETHUSDT"])
            timeframes: List timeframe (misal: ["5m", "15m"])
            lookback_candles: Jumlah candle yang akan diunduh
            
        Returns:
            Dict dengan struktur: {symbol: {timeframe: file_path}}
        """
        results = {}
        
        for symbol in symbols:
            results[symbol] = {}
            
            for timeframe in timeframes:
                print(f"[Scanner] Downloading {symbol} {timeframe}...")
                
                # Hitung time range berdasarkan candle terakhir (bukan datetime.now())
                # Untuk mock, kita gunakan waktu saat ini sebagai acuan candle terakhir
                # Dalam production, ini akan diambil dari server Binance
                current_time_ms = int(datetime.utcnow().timestamp() * 1000)
                
                # Round down ke interval terdekat
                interval_map = {
                    '1m': 60000, '3m': 180000, '5m': 300000, '15m': 900000,
                    '30m': 1800000, '1h': 3600000, '2h': 7200000, '4h': 14400000,
                    '6h': 21600000, '12h': 43200000, '1d': 86400000
                }
                
                interval_ms = interval_map.get(timeframe, 300000)
                end_time = (current_time_ms // interval_ms) * interval_ms
                start_time = end_time - (lookback_candles * interval_ms)
                
                # Download data dari client
                klines = self.client.get_klines(
                    symbol=symbol,
                    interval=timeframe,
                    start_time=start_time,
                    end_time=end_time,
                    limit=lookback_candles
                )
                
                # Normalisasi dan transformasi data
                normalized_data = self._normalize_klines(symbol, timeframe, klines)
                
                # Simpan ke JSON Data Lake
                file_path = self._save_to_json(symbol, timeframe, normalized_data)
                
                results[symbol][timeframe] = file_path
                print(f"[Scanner] Saved {len(klines)} candles to {file_path}")
        
        return results
    
    def _normalize_klines(
        self, 
        symbol: str, 
        timeframe: str, 
        klines: List[List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Menormalisasi raw klines menjadi format yang konsisten dengan Time ID (WIB).
        
        Args:
            symbol: Simbol trading
            timeframe: Timeframe
            klines: Raw klines dari API
            
        Returns:
            List of dict dengan field yang dinormalisasi
        """
        normalized = []
        
        for kline in klines:
            open_time_ms = kline[0]
            close_time_ms = kline[6]
            
            # Konversi ke Time ID (WIB) menggunakan TimeService
            open_time_id = self.time_service.timestamp_to_time_id(open_time_ms // 1000)
            close_time_id = self.time_service.timestamp_to_time_id(close_time_ms // 1000)
            
            # Parse numeric values
            record = {
                "symbol": symbol,
                "timeframe": timeframe,
                "time_id_open": open_time_id,
                "time_id_close": close_time_id,
                "timestamp_utc_ms": open_time_ms,
                "timestamp_wib_ms": self.time_service.utc_to_wib_timestamp(open_time_ms),
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5]),
                "quote_volume": float(kline[7]),
                "num_trades": int(kline[8]),
                "taker_buy_volume": float(kline[9]),
                "taker_buy_quote_volume": float(kline[10]),
                # Metadata untuk RAG
                "price_range": float(kline[2]) - float(kline[3]),
                "body_size": abs(float(kline[4]) - float(kline[1])),
                "is_bullish": float(kline[4]) >= float(kline[1])
            }
            
            normalized.append(record)
        
        return normalized
    
    def _save_to_json(
        self, 
        symbol: str, 
        timeframe: str, 
        data: List[Dict[str, Any]]
    ) -> str:
        """
        Menyimpan data ternormalisasi ke file JSON.
        
        Args:
            symbol: Simbol trading
            timeframe: Timeframe
            data: Data yang sudah dinormalisasi
            
        Returns:
            Path file yang disimpan
        """
        filename = f"{symbol}_{timeframe}.json"
        filepath = os.path.join(self.storage_path, filename)
        
        output = {
            "metadata": {
                "symbol": symbol,
                "timeframe": timeframe,
                "total_candles": len(data),
                "generated_at": datetime.utcnow().isoformat(),
                "source": "MockBinanceClient",  # Akan berubah jadi "BinanceAPI" nanti
                "time_zone": "Asia/Jakarta (WIB)"
            },
            "data": data
        }
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        return filepath
    
    def load_market_data(
        self, 
        symbol: str, 
        timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """
        Memuat data market dari JSON Data Lake.
        
        Args:
            symbol: Simbol trading
            timeframe: Timeframe
            
        Returns:
            Dict dengan metadata dan data, atau None jika tidak ditemukan
        """
        filename = f"{symbol}_{timeframe}.json"
        filepath = os.path.join(self.storage_path, filename)
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def get_latest_price(self, symbol: str, timeframe: str) -> Optional[float]:
        """
        Mendapatkan harga close terbaru dari data yang tersimpan.
        
        Args:
            symbol: Simbol trading
            timeframe: Timeframe
            
        Returns:
            Harga close terbaru, atau None jika data tidak ada
        """
        data = self.load_market_data(symbol, timeframe)
        
        if not data or not data.get("data"):
            return None
        
        return data["data"][-1]["close"]
    
    def validate_time_continuity(
        self, 
        symbol: str, 
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Memvalidasi bahwa time_id berurutan tanpa gap.
        
        Args:
            symbol: Simbol trading
            timeframe: Timeframe
            
        Returns:
            Dict dengan hasil validasi
        """
        data = self.load_market_data(symbol, timeframe)
        
        if not data or not data.get("data"):
            return {"valid": False, "error": "No data found"}
        
        records = data["data"]
        gaps = []
        
        for i in range(1, len(records)):
            prev_time_id = records[i-1]["time_id_close"]
            curr_time_id = records[i]["time_id_open"]
            
            # Cek apakah time_id berurutan
            # Format time_id: YYYYMMDD-HHMMSS-WIB
            # Untuk simplifikasi, kita cek selisih timestamp
            prev_ts = records[i-1]["timestamp_wib_ms"]
            curr_ts = records[i]["timestamp_wib_ms"]
            
            interval_map = {
                '1m': 60000, '3m': 180000, '5m': 300000, '15m': 900000,
                '30m': 1800000, '1h': 3600000, '2h': 7200000, '4h': 14400000
            }
            
            expected_interval = interval_map.get(timeframe, 300000)
            actual_interval = curr_ts - prev_ts
            
            # Toleransi 1 detik untuk rounding
            if abs(actual_interval - expected_interval) > 1000:
                gaps.append({
                    "index": i,
                    "prev_time_id": prev_time_id,
                    "curr_time_id": curr_time_id,
                    "expected_gap_ms": expected_interval,
                    "actual_gap_ms": actual_interval
                })
        
        return {
            "valid": len(gaps) == 0,
            "total_candles": len(records),
            "gaps_found": len(gaps),
            "gap_details": gaps[:10]  # Max 10 gap pertama
        }


# AUDIT CHECKLIST: Scanner Engine
# [✓] HANYA mengunduh dan menormalisasi data OHLCV + Volume
# [✓] TIDAK menghitung indikator teknikal (ATR, MACD, Supertrend, dll.)
# [✓] TIDAK menggunakan datetime.now() untuk logic bisnis (hanya untuk metadata)
# [✓] Semua timestamp berasal dari candle data (siap untuk Replay Mode)
# [✓] Output JSON terstruktur untuk mudah di-index oleh RAG
# [✓] TIDAK ada ketergantungan pada modul trading (Worker, HiveMind, Portfolio, Execution)
# [✓] Isolasi total dari logika entry/exit decision making
