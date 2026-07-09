### 📄 File 4: `04_WORKER_AND_EXECUTION_SPEC.md`
*(Berisi Strategi, Eksekusi, dan Manajemen Risiko)*

```markdown
# ST-LMS v3: Worker Ecosystem & Execution Specification

## 1. Workers (The Specialists)
Setiap strategi (Trend, Pullback, Breakout, Grid, OI, dll.) adalah **Plugin Independen** yang berada di foldernya masing-masing.
- **Local Memory & DNA:** Memiliki parameter dan memori lokal.
- **Read-Only:** Worker HANYA boleh membaca Truth Layer dan RAG. DILARANG mengubah Truth Layer.
- **Output:** Worker TIDAK PERNAH memanggil API Exchange untuk Buy/Sell. Mereka hanya mengeluarkan **Proposal**.

### Schema Proposal
```json
{
  "worker": "Pullback_v1",
  "type": "ENTRY",
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "confidence": 0.91,
  "evidence": [
    {"source": "WaveRAG", "fact": "UPTREND_LADDER"},
    {"source": "LineRAG", "fact": "Retest on L1001"}
  ],
  "reason": "Deep pullback to strong support with MACD bullish divergence"
}
---
