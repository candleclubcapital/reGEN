# reGEN
A Python GUI tool that resurrects lost NFT collections from metadata and layer directories. Handles rarity suffixes, inconsistent naming, and extensionless metadata.

<img width="507" height="498" alt="Screenshot 2025-10-14 at 5 11 37 PM" src="https://github.com/user-attachments/assets/6c5b7f75-68b8-4bbc-af77-1524317efe83" />

## ✨ Features
- Rebuild NFTs from extensionless JSON metadata
- Fuzzy layer matching (ignores `#`, `_`, and `-` rarity suffixes)
- Case-insensitive and punctuation-tolerant name resolution
- Multi-threaded with safe start/stop controls

---

## 🧩 Requirements
```bash
pip install PySide6 Pillow
