# ST-LMS v3: Core Architecture & Philosophy

## 1. Filosofi Inti (STRICT GUARDRAILS)
ST-LMS v3 BUKAN bot trading monolitik atau black-box AI. Ini adalah "Trading Operating System" yang berlandaskan pada **Truth-First Architecture**, **Data Truth**, dan **Pipeline Truth**.
- **Single Source of Truth:** "Truth Layer" (Supertrend Point, Line, Wave) adalah SATU-SATUNYA sumber kebenaran. Indikator lain (MACD, OI, Volume Delta) hanyalah validator (Power & Capital Layer).
- **No Direct Execution:** Worker TIDAK BOLEH trading langsung. Worker hanya mengeluarkan `Proposal`. HiveMind yang mengumpulkan, Portfolio Manager yang mengeksekusi.
- **No SQLite for Live Pipeline:** DILARANG KERAS menggunakan SQLite/PostgreSQL untuk pipeline live/real-time. Database hanya untuk Archive/Audit. Pipeline live wajib menggunakan JSON Data Lake + Memory Index.
- **No Vector DB / LLM:** DILARANG menggunakan Chroma, Pinecone, atau LLM untuk analisis market. Gunakan "Structural RAG" (JSON + Index + Binary Search).
- **WIB & Time ID:** Semua waktu WAJIB menggunakan WIB dan memiliki "Time ID" unik untuk memudahkan audit dan replay.

## 2. Pipeline Utama (The Flow)
1. **Scanner:** Download Raw Data (Candle, OI, Volume, Funding). Terpisah dari sistem trading.
2. **Normalizer:** Konversi UTC ke WIB, validasi gap, sinkronisasi Time ID.
3. **Observe:** Menghitung fakta mentah (ATR, EMA, MACD State, Volume Delta, OI).
4. **Semantic/Validation:** Menerjemahkan fakta menjadi kejadian (Pullback, Break, Retest, Compression).
5. **Truth Layer:** Membangun struktur pasar (Point → Line → Wave).
6. **Structural RAG:** Mencari "Trading Case" historis yang mirip.
7. **HiveMind:** Task Queue & Proposal Hub.
8. **Workers:** Strategi independen yang membaca Truth Layer (Read-Only) dan menghasilkan Proposal.
9. **Portfolio Manager:** Mengalokasikan modal berdasarkan skor Darwin/Academy. Worker yang tidak dapat modal masuk ke **Replay Mode**.
10. **Global Exit Manager:** Service global untuk Trailing, BE, TP, SL, dan Emergency Exit.

## 3. Aturan Eksekusi Kode
- TUNGGU PERINTAH: Bangun modul per modul (Sprint).
- TIAP FILE WAJIB MEMILIKI: Docstring, Type Hinting (Python typing), dan Error handling ke "Audit Log".
- DILARANG OVER-ENGINEERING: Gunakan `dataclass` atau `Pydantic` untuk schema JSON.
