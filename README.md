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
│           └── V4.3/
├── references/
│   ├── NOBI_TABLES.md
│   ├── THREAD_PILOT_TABLE.md
│   └── MATERIAL_RULES.md
└── regression/
    ├── datum/
    ├── bend/
    ├── topology/
    └── features/
```

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
