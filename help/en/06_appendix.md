# 💡 06. Appendix & Advanced Tips

Storage safety specifications, keyboard shortcuts, and open-source contribution guidelines.

---

## 🔒 Data Security & Retention Specifications

### 1. `_qfield_return` Timestamped Isolation
To protect master GIS datasets, the plugin **never overwrites original survey layers directly**:
* Every return payload is isolated in a dedicated timestamped snapshot directory:
  ```plaintext
  <ProjectRoot>/_qfield_return/2026-10-28_17-30-00_RedmiK40/
  ```
* Even if multiple field technicians submit layers with identical filenames at different times, all versions are neatly preserved.

### 2. Automatic Temporary Artifact Cleanup
* Project ZIP files generated during outbound packaging are automatically cleaned up when the dialog is closed or upon the next packaging run, preserving disk space.

---

## ⚡ Keyboard Shortcuts

| Shortcut / Action | Function |
| :--- | :--- |
| **Esc** | Close the Help Center or active dialog |
| **F5** (in Return Dialog) | Refresh LAN listening state and ledger list |
| **Right-Click Entry** (in Ledger) | Context menu: "Locate in File Explorer" or "Load into QGIS" |

---

## 📜 License & Community

* **License**: Published under the **GNU AGPL v3.0** (Affero General Public License).
* **Feedback & Bug Reports**:
  Found a bug or have a suggestion for remote field workflows? Submit an issue on our GitHub repository:
  [https://github.com/OpenQGIS/QFieldDrop](https://github.com/OpenQGIS/QFieldDrop)

Thank you for contributing to the open-source GIS community!
