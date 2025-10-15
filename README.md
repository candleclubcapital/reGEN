# reGEN
A Python GUI tool that resurrects lost NFT collections from metadata and layer directories. Handles rarity suffixes, inconsistent naming, and extensionless metadata.


## ✨ Features
- Rebuild NFTs from extensionless JSON metadata
- Fuzzy layer matching (ignores `#`, `_`, and `-` rarity suffixes)
- Case-insensitive and punctuation-tolerant name resolution
- Multi-threaded with safe start/stop controls

---

## 🧩 Requirements
```bash
pip install PySide6 Pillow
