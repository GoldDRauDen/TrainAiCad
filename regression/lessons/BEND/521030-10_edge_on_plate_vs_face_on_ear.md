# 521030-10 26-064689/064690 — a side view cannot tell an edge-on plate from a face-on ear

**FACT.** SUS304 t1.5, ① 三方曲げ (top plate 200 × 70 + front wall 100 + two ears) and ② 角度曲げ (rear wall 30 + slanted plate 93.76 at 138.29°). The side view draws top plate, front wall, rear wall and slanted plate as thick lines; the ears, seen face-on, add no line of their own because their outline is the same four edges. First build read the lines as edge-on plates only (a Π with a 30 wall, no ears); the checked sample has ears wrapping the outside, so the plates between them are 200 − 1.5 − 1.5 = 197 wide, and the slanted plate is part ② with the 30 wall.

**ROOT_CAUSE.** One outline served two readings and the face graph was chosen without evidence; the function cue (two Ø10 bars welded at both ends need a face) and the note 三方曲げ were not used.

**LESSON.** Count such a view UNKNOWN, list both graphs, ask before building (`BEND.md` §2). Section numbers that do not close (30, 100, 5 opening, t) give the slant by `lookup.py slant --width 70 --rise 70 --opening 5 --t 1.5` → 138.29°, 93.76, tip 7.62. A bend at 138.29° without a handwritten Nobi is `SPLIT_FLANGE_10MM` + FLAG; Ø48 vs Ø48.6 of the tube mark and a 70 + 28.5 split of the plate/rear wall were sent to the customer (`521030-10→質問.pdf`).
