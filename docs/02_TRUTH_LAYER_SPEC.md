# ST-LMS v3: Truth Layer Specification

Truth Layer tidak boleh menyimpan data yang bisa dihitung ulang secara deterministik (seperti distance, slope, atau duration). Ia hanya menyimpan fakta dasar, relasi, dan history pergeseran.

## 1. Time ID Format
Semua objek harus memiliki referensi waktu berdasarkan WIB.
Format: `[Prefix][YY][MM][DD][HH][mm]`
Contoh: `P2607081920` (Point, Tahun 2026, Bulan 07, Tgl 08, Jam 19, Menit 20 WIB).

## 2. Supertrend Point (Unit Terkecil)
```json
{
  "point_id": "P2607081920",
  "price": 61526.8,
  "type": "SUPPORT",      // Enum: "SUPPORT" | "RESISTANCE"
  "color": "GREEN",       // Enum: "GREEN" | "RED"
  "time_wib": "2026-07-08 19:20:00"
}

---
