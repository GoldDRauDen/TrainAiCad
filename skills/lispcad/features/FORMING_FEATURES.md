# LISPCAD Feature — Forming Features

Source: approved V4.3 production baseline.

### 3.2 3D Forming Features Mapping (To 2D Flat Pattern)
For 3D forming operations (which cannot be cut directly as flat outlines), map geometry into 2D laser manufacturing layers:

1. **Scribe / Marking Lines (Kegaki - Color 1 / Red)**:
   - Features: **Louver**, **Emboss**, **Dimple Outline**, **Rib**, **Gusset**, **Bridge**, **Half Shear**, **Hem**, **Curl**, **Lance Cut Line**.
   - CAD Representation: DXF Group `(62 . 1)` on Layer `"0"`. Indicates marking/bending reference for press operators.
2. **Pilot / Piercing Points (Piasu - Color 3 / Green)**:
   - Features: **Dimple Center Point**, **Burring Pilot Hole**, **Lance Piercing Point**, **Spot Welding Location**.
   - CAD Representation: DXF Group `(62 . 3)` on Layer `"0"`. Indicates laser piercing center location.

---
