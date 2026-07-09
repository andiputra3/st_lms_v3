### 📄 File 3: `03_RAG_AND_HIVEMIND_SPEC.md`
*(Berisi Otak Pencari Pengalaman & Koordinator)*

```markdown
# ST-LMS v3: Structural RAG & HiveMind Specification

## 1. Structural RAG (Relational/Graph Retriever)
DILARANG menggunakan Vector Database atau LLM. RAG di ST-LMS adalah "Pustakawan" yang menelusuri hubungan antar-objek menggunakan JSON + Dictionary Index + Binary Search.

### Unit Pencarian: Trading Case
RAG tidak mencari candle atau indikator tunggal. Unit pencariannya adalah **Trading Case** yang berisi:
- Kondisi Truth Layer (Wave, Line, Point)
- Power & Capital Layer (MACD State, OI Delta, Volume Delta)
- Proposal Worker yang aktif saat itu
- Outcome (Win/Loss, PnL, Reason)

### Fact Card (Format Standar Keluaran RAG)
Setiap pencarian dari Librarian (Point RAG, Line RAG, Wave RAG, OI RAG) harus mengembalikan format seragam:
```json
{
  "source": "LineRAG",
  "object_id": "L1001",
  "fact": "Strong Support, Retested 3 times",
  "confidence": 0.94,
  "references": ["P2607082235", "P2607082238"],
  "time_id": "P2607082241"
}


---
