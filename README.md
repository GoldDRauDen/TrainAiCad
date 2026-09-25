# TrainAiCad

TrainAiCad là môi trường huấn luyện và calibration AI theo quy trình CAD thực tế của người dùng.

Người dùng cung cấp công việc, bản vẽ, kết quả chuẩn và sửa các lỗi của AI. AI phải phân tích nguyên nhân, rút ra lesson và đề xuất các quy tắc có thể tái sử dụng.

Mỗi lesson chỉ được đưa vào production skill sau khi người dùng trực tiếp phê duyệt.

GitHub **không phải môi trường training**. Repository này chỉ lưu production skills đã được xác nhận, shared references, regression cases và tài liệu cần thiết để một AI mới có thể thực hiện công việc mà không cần lịch sử hội thoại trước đó.

## Production entry point

AI bắt đầu tại:

`AI_ENTRYPOINT.md`

## Architecture

```text
TrainAiCad/
├── README.md
├── AI_ENTRYPOINT.md
├── skills/
│   └── lispcad/
│       ├── core/
│       │   ├── DRAWING_READING.md
│       │   ├── DATUM_DIMENSION.md
│       │   ├── VALIDATION.md
│       │   └── CAD_OUTPUT.md
│       ├── modes/
│       │   ├── FLAT_NO_BEND.md
│       │   └── BEND_UNFOLD.md
│       ├── topology/
│       │   ├── U_PROFILE.md
│       │   ├── L_PROFILE.md
│       │   ├── STEPPED_PROFILE.md
│       │   └── MULTI_FACE_PROFILE.md
│       ├── features/
│       │   ├── HOLES_TAPS.md
│       │   ├── SLOTS.md
│       │   ├── CHAMFER_RADIUS.md
│       │   └── FORMING_FEATURES.md
│       ├── portable/
│       │   └── SKILL_LISPCAD_CURRENT.md
│       └── versions/
│           ├── V4.3/  (immutable baseline)
│           └── V4.4/  (approved 520924-19)
├── references/
│   ├── NOBI_TABLES.md
│   ├── THREAD_PILOT_TABLE.md
│   └── MATERIAL_RULES.md  (complete approved 2026-07-30 workbook transcription)
└── regression/
    ├── datum/
    ├── bend/
    ├── topology/
    └── features/
```

## Active approved production release (2026-09-25)

- **V4.4** from approved `520924-19` calibration is active. Read `AI_ENTRYPOINT.md` and the required modular files, or take the standalone `skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md`.
- Historical `skills/lispcad/versions/V4.3/` is unchanged. The immutable approved `skills/lispcad/versions/V4.4/` has the complete portable source including the 2026-07-30 Excel capability table.
- Material capability and automatic R: `references/MATERIAL_RULES.md`. Approved tests: `regression/features/520924-19_APPROVED.md`.
- **No Lisp/DXF was regenerated** for this skill-release operation; unapproved construction of `055958` shop relief and the exact special J in `055957` remain pending.

## Operating model

1. Train/calibrate trong dự án TrainAiCad.
2. AI phân tích lỗi và đề xuất lesson/rule.
3. Người dùng trực tiếp phê duyệt từng lesson.
4. Chỉ lesson đã phê duyệt mới được cập nhật vào production module hoặc regression case.
5. Core chứa rule dùng chung; module chỉ chứa specialization để tránh duplicate rule.
6. Portable skill là bản single-file để mang sang môi trường không đọc được toàn repo.
7. Immutable version snapshots được giữ trong `skills/lispcad/versions/`.

## Approval rule

**No approved lesson, no production skill update.**
