"""
Binance Futures Client Wrapper

Module ini bertanggung jawab untuk mengambil data OHLCV dari Binance Futures API.
Untuk saat ini menggunakan MockClient untuk testing tanpa rate-limit.
Struktur siap diganti dengan implementasi requests/ccxt asli.
"""

import random
import math
from typing import List, Dict, Any, Optional
from datetime import datetime


class MockBinanceClient:
    """
    Mock client untuk mensimulasikan respons API Binance Futures.
    Endpoint: /fapi/v1/klines
    
    Struktur respons meniru format asli Binance untuk kemudahan migrasi nanti.
    """
    
    BASE_URL = "https://fapi.binance.com"
    ENDPOINT = "/fapi/v1/klines"
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Inisialisasi client.
        
        Args:
            api_key: Binance API Key (tidak digunakan untuk mock)
            api_secret: Binance API Secret (tidak digunakan untuk mock)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self._session_id = random.randint(1000, 9999)
    
    def get_klines(
        self, 
        symbol: str, 
        interval: str, 
        start_time: int, 
        end_time: int, 
        limit: int = 500
    ) -> List[List[Any]]:
        """
        Mengambil data kline/OHLCV dari Binance Futures.
        
        Args:
            symbol: Simbol trading (misal: BTCUSDT)
            interval: Timeframe (misal: 5m, 15m, 1h)
            start_time: Timestamp mulai (ms)
            end_time: Timestamp akhir (ms)
            limit: Jumlah maksimal candle (max 500 untuk Binance)
            
        Returns:
            List of klines dengan format:
            [
                [
                    open_time,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    close_time,
                    quote_asset_volume,
                    number_of_trades,
                    taker_buy_base_asset_volume,
                    taker_buy_quote_asset_volume,
                    ignore
                ],
                ...
            ]
        """
        # Generate dummy data yang realistis menggunakan pola sinusoidal
        return self._generate_mock_klines(symbol, interval, start_time, end_time, limit)
    
    def _generate_mock_klines(
        self, 
        symbol: str, 
        interval: str, 
        start_time: int, 
        end_time: int, 
        limit: int
    ) -> List[List[Any]]:
        """Generate mock OHLCV data dengan pola yang realistis."""
        
        # Parse interval untuk mendapatkan durasi dalam menit
        interval_map = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720,
            '1d': 1440, '3d': 4320, '1w': 10080
        }
        
        interval_minutes = interval_map.get(interval, 5)
        interval_ms = interval_minutes * 60 * 1000
        
        # Hitung jumlah candle yang dibutuhkan
        total_candles = min(limit, (end_time - start_time) // interval_ms + 1)
        
        # Seed berdasarkan simbol agar konsisten per simbol
        seed_value = sum(ord(c) for c in symbol) + self._session_id
        random.seed(seed_value)
        
        # Harga awal berdasarkan simbol (BTC ~95k, ETH ~3.5k, dll)
        base_prices = {
            'BTC': 95000,
            'ETH': 3500,
            'SOL': 180,
            'BNB': 600,
            'XRP': 2.5,
            'ADA': 1.0,
            'DOGE': 0.35,
            'AVAX': 40,
            'LINK': 25,
            'MATIC': 0.8
        }
        
        # Deteksi base asset dari simbol
        base_asset = symbol.replace('USDT', '').replace('BUSD', '')
        base_price = base_prices.get(base_asset[:3], 100.0)
        
        klines = []
        current_time = start_time
        current_price = base_price
        
        # Volatilitas berdasarkan interval (lebih pendek = lebih volatil)
        volatility = 0.02 / math.sqrt(interval_minutes)
        
        for i in range(total_candles):
            if current_time > end_time:
                break
            
            # Generate pergerakan harga menggunakan random walk dengan drift
            drift = math.sin(i / 20) * 0.005  # Pola sinusoidal untuk trend
            random_change = random.gauss(0, volatility)
            price_change = drift + random_change
            
            open_price = current_price
            close_price = open_price * (1 + price_change)
            
            # High dan Low harus membungkus open dan close
            candle_range = abs(close_price - open_price) * (1 + random.random() * 0.5)
            high_price = max(open_price, close_price) * (1 + random.random() * 0.005)
            low_price = min(open_price, close_price) * (1 - random.random() * 0.005)
            
            # Volume: lebih tinggi saat pergerakan besar
            base_volume = random.uniform(100, 1000)
            volume = base_volume * (1 + abs(price_change) * 10)
            
            # Taker buy volume (sekitar 50-60% dari total volume)
            taker_buy_ratio = random.uniform(0.45, 0.65)
            taker_buy_volume = volume * taker_buy_ratio
            
            close_time = current_time + interval_ms - 1
            
            kline = [
                current_time,                                    # 0: Open time
                f"{open_price:.2f}",                             # 1: Open
                f"{high_price:.2f}",                             # 2: High
                f"{low_price:.2f}",                              # 3: Low
                f"{close_price:.2f}",                            # 4: Close
                f"{volume:.2f}",                                 # 5: Volume
                close_time,                                      # 6: Close time
                f"{volume * close_price:.2f}",                   # 7: Quote asset volume
                random.randint(500, 5000),                       # 8: Number of trades
                f"{taker_buy_volume:.2f}",                       # 9: Taker buy base volume
                f"{taker_buy_volume * close_price:.2f}",         # 10: Taker buy quote volume
                "0"                                              # 11: Ignore
            ]
            
            klines.append(kline)
            
            current_price = close_price
            current_time += interval_ms
        
        # Reset random seed
        random.seed()
        
        return klines
    
    def get_symbol_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Mengambil harga ticker terakhir untuk simbol.
        
        Args:
            symbol: Simbol trading
            
        Returns:
            Dict dengan informasi ticker
        """
        # Mock response
        return {
            "symbol": symbol,
            "price": f"{random.uniform(100, 100000):.2f}",
            "time": int(datetime.utcnow().timestamp() * 1000)
        }


# ============================================================================
# CATATAN UNTUK IMPLEMENTASI ASLI (menggunakan requests atau ccxt)
# ============================================================================
# 
# Untuk mengganti dengan implementasi asli, buat kelas baru atau modifikasi:
#
# import requests
# import hmac
# import hashlib
# import time
#
# class RealBinanceClient:
#     def __init__(self, api_key: str, api_secret: str):
#         self.api_key = api_key
#         self.api_secret = api_secret
#         self.session = requests.Session()
#         self.session.headers.update({
#             'X-MBX-APIKEY': self.api_key
#         })
#     
#     def _sign_request(self, params: dict) -> dict:
#         query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
#         signature = hmac.new(
#             self.api_secret.encode('utf-8'),
#             query_string.encode('utf-8'),
#             hashlib.sha256
#         ).hexdigest()
#         params['signature'] = signature
#         return params
#     
#     def get_klines(self, symbol: str, interval: str, start_time: int, 
#                    end_time: int, limit: int = 500) -> List[List[Any]]:
#         params = {
#             'symbol': symbol,
#             'interval': interval,
#             'startTime': start_time,
#             'endTime': end_time,
#             'limit': limit,
#             'recvWindow': 5000,
#             'timestamp': int(time.time() * 1000)
#         }
#         
#         params = self._sign_request(params)
#         
#         url = f"{self.BASE_URL}{self.ENDPOINT}"
#         response = self.session.get(url, params=params)
#         response.raise_for_status()
#         
#         return response.json()
# ============================================================================
