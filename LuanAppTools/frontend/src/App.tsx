import React, { useState, useEffect, useRef } from "react";
import { loadEvents } from "./events";
type RecordData = Record<string, any>;
const statuses: Record<string, string> = {
  discovered: "Mới phát hiện",
  queued: "Đang xếp hàng",
  running: "Đang xử lý",
  pause_requested: "Đang yêu cầu dừng",
  paused: "Đã tạm dừng",
  waiting_usage: "Chờ usage",
  waiting_fallback: "Chờ chọn dự phòng",
  waiting_output: "Chờ ghi LAN",
  reconciliation_required: "Cần đối soát phiên",
  completed: "Hoàn tất",
  error: "Lỗi",
  cancelled: "Đã hủy",
  superseded: "Nguồn đã thay thế",
};
const label = (s: string) => statuses[s] || s;
const number = (v: unknown) =>
  typeof v === "number" ? v.toLocaleString("vi-VN") : "Chưa có dữ liệu";
export function App() {
  const [tab, setTab] = useState("jobs"),
    [jobs, setJobs] = useState<RecordData[]>([]),
    [health, setHealth] = useState<RecordData>({}),
    [settings, setSettings] = useState<RecordData | null>(null),
    [connections, setConnections] = useState<RecordData>({}),
    [providers, setProviders] = useState<RecordData>({}),
    [selected, setSelected] = useState<string[]>([]),
    [search, setSearch] = useState(""),
    [filter, setFilter] = useState(""),
    [detail, setDetail] = useState<RecordData | null>(null),
    [detailId, setDetailId] = useState(""),
    [events, setEvents] = useState<RecordData[]>([]),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [difficulty, setDifficulty] = useState("auto"),
    [individual, setIndividual] = useState<boolean | null>(null);
  const token = useRef("");
  const detailSequence = useRef(0);
  async function api(url: string, method?: string, body?: unknown) {
    const r = await fetch(
      url,
      method
        ? {
            method,
            headers: {
              "Content-Type": "application/json",
              "X-Luan-Token": token.current,
            },
            body: JSON.stringify(body ?? {}),
          }
        : undefined,
    );
    const data = await r.json();
    if (!r.ok) throw Error(data.error?.message || `HTTP ${r.status}`);
    return data;
  }
  async function refresh() {
    const [h, j] = await Promise.all([api("/api/health"), api("/api/jobs")]);
    token.current = h.mutation_token;
    setHealth(h);
    setJobs(j.jobs);
  }
  async function verifyConnection(provider: string) {
    try {
      return await api("/api/connections/test", "POST", { provider });
    } finally {
      setProviders(await api("/api/providers"));
      setConnections(await api("/api/connections"));
    }
  }
  async function loadDetail(id: string) {
    const sequence = ++detailSequence.current;
    const d = await api(`/api/jobs/${id}`);
    const e = d.run?.id
      ? await loadEvents(api, id, () => sequence === detailSequence.current, d.run.id)
      : [];
    if (sequence === detailSequence.current) {
      setDetail(d);
      setEvents(e);
    }
  }
  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        await refresh();
        const [s, p, c] = await Promise.all([
          api("/api/settings"),
          api("/api/providers"),
          api("/api/connections"),
        ]);
        if (alive) {
          setSettings(s);
          setProviders(p);
          setConnections(c);
        }
      } catch (e) {
        if (alive) setError(String((e as Error).message));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    const timer = setInterval(() => {
      void refresh().catch((e) => setError(e.message));
    }, 3000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    if (!detailId) return;
    void loadDetail(detailId).catch((e) => setError(e.message));
    const timer = setInterval(() => {
      void loadDetail(detailId).catch((e) => setError(e.message));
    }, 5000);
    return () => {
      clearInterval(timer);
      detailSequence.current++;
    };
  }, [detailId]);
  async function action(
    fn: () => Promise<unknown>,
    message: string | ((result: unknown) => string) = "Đã cập nhật",
  ) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await fn();
      await refresh();
      if (detailId) await loadDetail(detailId);
      setNotice(typeof message === "function" ? message(result) : message);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const totals: Record<string, number> = {};
  jobs.forEach((j) =>
    Object.entries(j.technical_counts || {}).forEach(
      ([k, v]) => (totals[k] = (totals[k] || 0) + Number(v)),
    ),
  );
  const visible = jobs.filter(
    (j) =>
      (!filter || j.status === filter) &&
      `${j.name || j.display_name} ${j.folder}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">L</span>
          <div>
            LuanAppTools<small>TRAINAICAD WORKSPACE</small>
          </div>
        </div>
        <div className="nav-title">KHÔNG GIAN LÀM VIỆC</div>
        <button
          className={tab === "jobs" ? "nav active" : "nav"}
          onClick={() => setTab("jobs")}
        >
          ▦ <span>Công việc</span>
          <b>{jobs.length}</b>
        </button>
        <button
          aria-label="Cài đặt"
          className={tab === "settings" ? "nav active" : "nav"}
          onClick={() => setTab("settings")}
        >
          ⚙ <span>Cài đặt</span>
        </button>
        <div className="sidebar-bottom">
          <span className="dot" />
          Ứng dụng local<small>Mỗi job · một agent xuyên suốt</small>
          <p>Kết quả để kiểm tra thủ công.</p>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <div className="eyebrow">WORKSPACE / CAD AUTOMATION</div>
            <h1>{tab === "jobs" ? "Bảng công việc" : "Cài đặt vận hành"}</h1>
            <p>Chọn bản vẽ. Chạy một agent. Nhận DXF đã kiểm tra bằng công cụ local.</p>
          </div>
          <span className="connection">
            <span className="dot" />
            {health.status === "ok" ? "Đã kết nối local" : "Đang kết nối"}
          </span>
        </header>
        {error && (
          <div role="alert" className="alert">
            {error}
            <button onClick={() => setError("")} aria-label="Đóng lỗi">
              ×
            </button>
          </div>
        )}
        {notice && (
          <div role="status" className="notice">
            {notice}
          </div>
        )}
        {tab === "jobs" ? (
          <>
            <div className="workflow-banner">
              <div><span className="eyebrow">QUY TRÌNH ĐƠN GIẢN</span><h2>Một job. Một agent.</h2><p>Cùng hội thoại từ đọc bản vẽ đến hoàn tất. Xem job không gọi AI.</p></div>
              <ol aria-label="Quy trình xử lý"><li><b>01</b> Đọc nguồn</li><li><b>02</b> Dựng hình</li><li><b>03</b> Kiểm tra & xuất</li></ol>
            </div>
            <div className="stats">
              {[
                ["Tổng công việc", jobs.length],
                ["Đang xử lý", health.active_jobs || 0],
                [
                  "Chờ / tạm dừng",
                  jobs.filter(
                    (j) =>
                      j.status.startsWith("waiting") ||
                      [
                        "queued",
                        "paused",
                        "pause_requested",
                        "reconciliation_required",
                      ].includes(j.status),
                  ).length,
                ],
                ["Lỗi", jobs.filter((j) => j.status === "error").length],
                [
                  "Chưa kiểm tra",
                  jobs.filter((j) => j.status === "completed" && !j.reviewed)
                    .length,
                ],
              ].map(([name, value]) => (
                <div className="stat" key={name}>
                  <span>{name}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
            <div className="technical">
              <span>TRẠNG THÁI KỸ THUẬT THEO MÃ</span>
              {["PASS", "REVIEW", "PREVIEW", "VIEWS_ONLY", "FLAG"].map((s) => (
                <span
                  key={s}
                  className={`badge ${s === "PASS" ? "good" : "warn"}`}
                >
                  {s} <b>{totals[s] || 0}</b>
                </span>
              ))}
              <small>
                {health.active_ai_calls || 0} lượt AI đang hoạt động
              </small>
            </div>
            <section className="panel">
              <div className="toolbar">
                <div>
                  <h2>Danh sách công việc</h2>
                  <span className="muted">
                    Chọn job cần xử lý, sau đó bấm Chạy đã chọn.
                  </span>
                </div>
                <button
                  disabled={busy}
                  onClick={() =>
                    action(() => api("/api/scan", "POST"), "Đã quét thư mục")
                  }
                >
                  ↻ Quét thư mục
                </button>
              </div>
              <div className="filters">
                <input
                  aria-label="Tìm công việc"
                  placeholder="Tìm mã job hoặc đường dẫn…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                <select
                  aria-label="Lọc trạng thái"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="">Tất cả trạng thái</option>
                  {Object.entries(statuses).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Xuất DXF riêng"
                  value={individual === null ? "default" : String(individual)}
                  onChange={(e) =>
                    setIndividual(
                      e.target.value === "default"
                        ? null
                        : e.target.value === "true",
                    )
                  }
                >
                  <option value="default">DXF riêng: theo cài đặt</option>
                  <option value="true">Xuất riêng mã PASS</option>
                  <option value="false">Chỉ DXF tổng</option>
                </select>
                <button
                  className="primary"
                  disabled={busy || !selected.length || !token.current}
                  onClick={() =>
                    action(async () => {
                      for (const id of selected)
                        await api(`/api/jobs/${id}/start`, "POST", {
                          difficulty,
                          ...(individual === null ? {} : { individual }),
                        });
                      setSelected([]);
                    }, "Đã xếp hàng các job đã chọn")
                  }
                >
                  Chạy đã chọn ({selected.length})
                </button>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th></th>
                      <th>Công việc / thư mục nguồn</th>
                      <th>Vận hành</th>
                      <th>Kỹ thuật</th>
                      <th>Kiểm tra thủ công</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map((j) => (
                      <tr key={j.id}>
                        <td>
                          <input
                            type="checkbox"
                            aria-label={`Chọn ${j.name || j.display_name}`}
                            checked={selected.includes(j.id)}
                            onChange={(e) =>
                              setSelected(
                                e.target.checked
                                  ? [...selected, j.id]
                                  : selected.filter((id) => id !== j.id),
                              )
                            }
                          />
                        </td>
                        <td>
                          <button
                            className="job-name"
                            onClick={() => {
                              setDetail(null);
                              setDetailId(j.id);
                            }}
                          >
                            {j.name || j.display_name}
                          </button>
                          <small className="path">{j.folder}</small>
                        </td>
                        <td>
                          <span
                            className={`badge ${j.status === "completed" ? "good" : j.status === "error" ? "bad" : j.status === "running" ? "blue" : "neutral"}`}
                          >
                            {label(j.status)}
                          </span>
                          <small>
                            {j.provider === "openai" ? "GPT" : j.provider === "custom" ? "Custom" : j.provider === "9router" ? "9Router" : "Claude"}
                            {j.run?.error && " · Có thông báo"}
                          </small>
                        </td>
                        <td>
                          {Object.keys(j.technical_counts || {}).length ? (
                            Object.entries(j.technical_counts).map(([s, n]) => (
                              <small key={s}>
                                {s}: {String(n)}
                              </small>
                            ))
                          ) : (
                            <span className="muted">Chưa có kết quả</span>
                          )}
                        </td>
                        <td>
                          {j.status === "completed"
                            ? j.reviewed
                              ? "Đã ghi nhận kiểm tra"
                              : "Chưa kiểm tra"
                            : "—"}
                        </td>
                        <td>
                          <button
                            onClick={() => {
                              setDetail(null);
                              setDetailId(j.id);
                            }}
                          >
                            Chi tiết →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!visible.length && (
                <div className="empty">
                  <div className="empty-icon">▱</div>
                  <h3>
                    {loading
                      ? "Đang tải công việc…"
                      : "Chưa có công việc phù hợp"}
                  </h3>
                  <p>
                    Thêm thư mục nguồn trong Cài đặt, sau đó quét và chọn job.
                  </p>
                  <button onClick={() => setTab("settings")}>
                    Thiết lập thư mục nguồn
                  </button>
                </div>
              )}
            </section>
            <p className="footnote">
              PASS kỹ thuật và xác nhận đã kiểm tra là hai trạng thái riêng. Mọi
              DXF đều cần anh kiểm tra lại.
            </p>
          </>
        ) : settings ? (
          <SettingsForm
            value={settings}
            providers={providers}
            connections={connections}
            busy={busy}
            saveConnection={(connection) =>
              action(async () => {
                setConnections(await api("/api/connections", "PUT", connection));
                await verifyConnection(connection.active_provider);
              }, "Đã lưu và kết nối thành công")
            }
            testConnection={(provider) =>
              action(async () => {
                await verifyConnection(provider);
              }, "Kết nối hoạt động")
            }
            loginClaude={() =>
              action(async () => {
                const result = await api("/api/connections/claude/login", "POST");
                setProviders(await api("/api/providers"));
                setConnections(await api("/api/connections"));
                return result;
              }, (result) => (result as RecordData).message)
            }
            save={(s) =>
              action(
                async () => setSettings(await api("/api/settings", "PUT", s)),
                "Đã lưu cài đặt",
              )
            }
          />
        ) : (
          <p>Đang tải cài đặt…</p>
        )}
      </main>
      {detailId && (
        <div className="drawer-backdrop">
          <section className="drawer" aria-label="Chi tiết công việc">
            <div className="toolbar">
              <div>
                <div className="eyebrow">HỒ SƠ CÔNG VIỆC</div>
                <h2>{detail?.name || "Đang tải…"}</h2>
              </div>
              <button
                aria-label="Đóng chi tiết"
                onClick={() => {
                  setDetailId("");
                  setDetail(null);
                }}
              >
                ×
              </button>
            </div>
            {detail && (
              <>
                <span className="badge blue">{label(detail.status)}</span>
                <p className="muted">{detail.run?.config?.single_agent ? "Một agent · cùng hội thoại · kiểm tra local" : detail.run ? "Lượt chạy cũ" : "Sẵn sàng chạy với một agent"}</p>
                <p className="path">{detail.folder}</p>
                {detail.workspace_path && <p className="path">Workspace: {detail.workspace_path}</p>}
                {detail.snapshot_path && <p className="path">Bản nguồn cố định: {detail.snapshot_path}</p>}
                {detail.source_profile && (
                  <p className="muted">
                    Nguồn local: {detail.source_profile.pages} trang PDF, {detail.source_profile.pages_without_text} trang gần như không có chữ trích xuất.
                    {detail.source_profile.pages >= 5 && " Job nhiều trang: bước đọc nguồn có thể dùng nhiều quota."}
                  </p>
                )}
                {detail.run?.error && (
                  <p className="alert">{detail.run.error}</p>
                )}
                <div className="actions">
                  {[
                    "queued",
                    "running",
                    "publication_pending",
                    "waiting_output",
                    "waiting_usage",
                    "waiting_fallback",
                  ].includes(detail.status) && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        action(() =>
                          api(`/api/jobs/${detail.id}/pause`, "POST"),
                        )
                      }
                    >
                      Tạm dừng
                    </button>
                  )}
                  {([
                    "paused",
                    "waiting_output",
                    "waiting_usage",
                    "waiting_fallback",
                  ].includes(detail.status) || (detail.status === "error" && detail.run?.config?.single_agent)) && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        action(() =>
                          api(`/api/jobs/${detail.id}/resume`, "POST"),
                        )
                      }
                    >
                      Tiếp tục
                    </button>
                  )}
                  {[
                    "paused",
                    "error",
                    "cancelled",
                    "waiting_output",
                    "waiting_usage",
                    "waiting_fallback",
                    "reconciliation_required",
                  ].includes(detail.status) && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        action(
                          () =>
                            api(`/api/jobs/${detail.id}/export-saved`, "POST", {
                              drafts: true,
                            }),
                          "Đã xuất lại từ các mã đã chốt, không gọi AI",
                        )
                      }
                    >
                      Xuất từ phần đã chốt (không gọi AI)
                    </button>
                  )}
                  {![
                    "discovered",
                    "completed",
                    "error",
                    "cancelled",
                    "superseded",
                  ].includes(detail.status) && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        action(() =>
                          api(`/api/jobs/${detail.id}/cancel`, "POST"),
                        )
                      }
                    >
                      Hủy
                    </button>
                  )}
                  {["completed", "error", "cancelled", "reconciliation_required"].includes(
                    detail.status,
                  ) && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        action(() =>
                          api(`/api/jobs/${detail.id}/start`, "POST", {
                            force: true,
                            difficulty,
                            ...(individual === null ? {} : { individual }),
                          }),
                        )
                      }
                    >
                      Chạy lại từ nguồn
                    </button>
                  )}
                  {[
                    "waiting_fallback",
                    "waiting_usage",
                    "reconciliation_required",
                  ].includes(detail.status) && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        action(
                          () =>
                            api(
                              `/api/jobs/${detail.id}/use-gateway`,
                              "POST",
                              {},
                            ),
                          "Đã yêu cầu kiểm tra và tiếp tục bằng kết nối AI đã chọn",
                        )
                      }
                    >
                      Tiếp tục bằng kết nối đã chọn
                    </button>
                  )}
                </div>
                <h3>Kết quả & kiểm tra</h3>
                <div className="actions">
                  <button
                    onClick={() =>
                      action(() =>
                        api(`/api/jobs/${detail.id}/open-folder`, "POST", {
                          target: "source",
                        }),
                      )
                    }
                  >
                    Mở Output tổng / nguồn
                  </button>
                  {detail.individual_output_available && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        action(() =>
                          api(`/api/jobs/${detail.id}/open-folder`, "POST", {
                            target: "individual",
                          }),
                        )
                      }
                    >
                      Mở Output riêng
                    </button>
                  )}
                </div>
                {detail.run?.config?.individual && !detail.individual_output_available && (
                  <p className="muted">Output riêng chưa được tạo cho lượt chạy hiện tại.</p>
                )}
                {detail.status === "completed" && (
                  <label className="review">
                    <input
                      type="checkbox"
                      checked={detail.reviewed}
                      disabled={busy}
                      onChange={(e) =>
                        action(() =>
                          api(`/api/jobs/${detail.id}/review`, "POST", {
                            run_id: detail.run.id,
                            reviewed: e.target.checked,
                          }),
                        )
                      }
                    />
                    Tôi đã kiểm tra kết quả của phiên bản này
                  </label>
                )}
                <p className="muted">
                  Xác nhận này không thay đổi trạng thái kỹ thuật.
                </p>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Mã</th>
                        <th>Trạng thái</th>
                        <th>Lượt giải</th>
                        <th>Bằng chứng / vấn đề</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(detail.parts || []).map((p: RecordData) => (
                        <tr key={p.code}>
                          <td>{p.code}</td>
                          <td>{p.status}</td>
                          <td>{p.attempts} / 2</td>
                          <td>
                            <details>
                              <summary>Xem hồ sơ</summary>
                              <pre>{JSON.stringify(p.data, null, 2)}</pre>
                            </details>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <h3>Nguồn & bản vẽ xuất</h3>
                <Preview job={detail} key={detail.id + detail.run?.id} />
                <h3>Usage đo được</h3>
                <div className="usage">
                  {Object.keys(detail.usage || {}).length ? (
                    Object.entries(detail.usage).map(([k, v]) => (
                      <span key={k}>
                        {k}
                        <strong>{number(v)}</strong>
                      </span>
                    ))
                  ) : (
                    <p>Chưa có dữ liệu usage</p>
                  )}
                </div>
                {Object.keys(detail.usage || {}).length > 0 && (
                  <p className="muted">
                    Input thực đã ghi (gồm cache): {number(
                      (detail.usage.input_tokens || 0) +
                      (detail.usage.cache_creation_input_tokens || 0) +
                      (detail.usage.cache_read_input_tokens || 0),
                    )} token · Output: {number(detail.usage.output_tokens || 0)} token.
                    Đây không phải phần trăm quota tài khoản.
                  </p>
                )}
                {Number(detail.unmeasured_job_requests || 0) > 0 && (
                  <p className="alert">
                    {detail.unmeasured_job_requests} lần gọi provider của job này không có usage cuối cùng (bị ngắt hoặc lỗi). Chi phí thực tế của các lần này chưa xác định.
                  </p>
                )}
                {Object.entries(detail.usage_by_stage || {}).map(([stage, metrics]) => (
                  <p className="muted" key={stage}>
                    {stage}: {Object.entries(metrics as RecordData).map(([key, value]) => `${key} ${number(value)}`).join(" · ")}
                  </p>
                ))}
                {Object.entries(detail.request_stats || {}).map(([stage, stats]) => (
                  <p className="muted" key={stage + "-requests"}>
                    {stage}: {(stats as RecordData).calls} lượt, {number((stats as RecordData).prompt_characters)} ký tự prompt, {(stats as RecordData).image_count} ảnh.
                  </p>
                ))}
                <p className="muted">
                  Phần dùng chung:{" "}
                  {Object.keys(detail.shared_overhead_usage || {}).length
                    ? JSON.stringify(detail.shared_overhead_usage)
                    : "Chưa có dữ liệu"}
                  . Không suy đoán quota tài khoản.
                </p>
                <p>
                  Đang hoạt động:{" "}
                  {Math.round(detail.durations?.active_seconds || 0)} giây · Tạm
                  dừng: {Math.round(detail.durations?.paused_seconds || 0)} giây
                  · Chờ: {Math.round(detail.durations?.waiting_seconds || 0)}{" "}
                  giây
                </p>
                <h3>Hoạt động gần nhất</h3>
                <div className="timeline">
                  {events
                    .slice(-40)
                    .reverse()
                    .map((e) => (
                      <div key={e.id}>
                        <time>
                          {new Date(e.created * 1000).toLocaleTimeString(
                            "vi-VN",
                          )}
                        </time>
                        <strong>{e.kind}</strong>
                        <pre>{JSON.stringify(e.payload, null, 2)}</pre>
                      </div>
                    ))}
                </div>
                <h3>Lịch sử lần chạy</h3>
                {(detail.runs || []).map((r: RecordData) => (
                  <details key={r.id}>
                    <summary>
                      {new Date(r.created * 1000).toLocaleString("vi-VN")} ·{" "}
                      {label(r.status)}
                    </summary>
                    <p>Rules commit: {r.repo_commit}</p>
                    <p>Nguồn: {r.source_hash}</p>
                  </details>
                ))}
                <h3>Lịch sử xác nhận kiểm tra</h3>
                {(detail.reviews || []).map((r: RecordData, i: number) => (
                  <p key={i}>
                    {r.reviewer} ·{" "}
                    {r.reviewed ? "Đã kiểm tra" : "Thu hồi xác nhận"} · {r.note}
                  </p>
                ))}
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
function Preview({ job }: { job: RecordData }) {
  const files = (job.files || []).filter((f: RecordData) => f.download_url);
  const [id, setId] = useState(""),
    [page, setPage] = useState(1),
    [zoom, setZoom] = useState(1);
  const viewport = useRef<HTMLDivElement>(null),
    drag = useRef<{ x: number; y: number; left: number; top: number } | null>(
      null,
    );
  const file = files.find((f: RecordData) => f.id === id) || files[0];
  const image =
    file &&
    (file.name.toLowerCase().endsWith(".dxf")
      ? `/api/jobs/${job.id}/preview/${file.id}`
      : file.pages_url
        ? file.pages_url.replace("{page}", String(page))
        : file.kind === "page"
          ? file.download_url
          : null);
  return (
    <>
      <select
        aria-label="Chọn bản vẽ xem trước"
        value={file?.id || ""}
        onChange={(e) => {
          setId(e.target.value);
          setPage(1);
          setZoom(1);
        }}
      >
        <option value="" disabled>
          Chọn file
        </option>
        {files.map((f: RecordData) => (
          <option key={f.id} value={f.id}>
            {f.name}
            {f.stale ? " · Lịch sử" : ""}
          </option>
        ))}
      </select>
      {file && (
        <>
          <div className="actions">
            <a href={file.download_url} download>
              Tải {file.name}
            </a>
            {file.page_count && (
              <label>
                Trang{" "}
                <input
                  type="number"
                  min={1}
                  max={file.page_count}
                  value={page}
                  onChange={(e) =>
                    setPage(
                      Math.max(
                        1,
                        Math.min(file.page_count, Number(e.target.value)),
                      ),
                    )
                  }
                />
              </label>
            )}
            <button onClick={() => setZoom(Math.max(0.25, zoom - 0.25))}>
              −
            </button>
            <span>{Math.round(zoom * 100)}%</span>
            <button onClick={() => setZoom(Math.min(5, zoom + 0.25))}>+</button>
            <button onClick={() => setZoom(1)}>Vừa khung</button>
          </div>
          {file.stale && (
            <p className="alert">Bản lịch sử; không phải kết quả hiện tại.</p>
          )}
          {image ? (
            <div
              className="preview"
              ref={viewport}
              onPointerDown={(e) => {
                if (viewport.current) {
                  drag.current = {
                    x: e.clientX,
                    y: e.clientY,
                    left: viewport.current.scrollLeft,
                    top: viewport.current.scrollTop,
                  };
                  e.currentTarget.setPointerCapture(e.pointerId);
                }
              }}
              onPointerUp={() => {
                drag.current = null;
              }}
              onPointerMove={(e) => {
                if (drag.current && viewport.current) {
                  viewport.current.scrollLeft =
                    drag.current.left + drag.current.x - e.clientX;
                  viewport.current.scrollTop =
                    drag.current.top + drag.current.y - e.clientY;
                }
              }}
            >
              <img
                src={image}
                alt={`Xem trước ${file.name}`}
                draggable={false}
                style={{ width: `${zoom * 100}%`, maxWidth: "none" }}
              />
            </div>
          ) : (
            <p>Chọn PDF hoặc DXF để xem trước.</p>
          )}
        </>
      )}
    </>
  );
}
function SettingsForm({
  value,
  providers,
  connections,
  busy,
  saveConnection,
  testConnection,
  loginClaude,
  save,
}: {
  value: RecordData;
  providers: RecordData;
  connections: RecordData;
  busy: boolean;
  saveConnection: (v: RecordData) => unknown;
  testConnection: (provider: string) => unknown;
  loginClaude: () => unknown;
  save: (v: RecordData) => unknown;
}) {
  const [form, setForm] = useState(value),
    [roots, setRoots] = useState((value.roots || []).join("\n"));
  const [connection, setConnection] = useState<RecordData>({
    active_provider: connections.active_provider || "claude",
    openai_model: connections.openai?.model || "",
    gateway_url: connections.custom?.endpoint || value.gateway_url || "http://localhost:20128/v1",
    gateway_model: connections.custom?.model || value.gateway_model || "",
    gateway_effort: value.gateway_effort || "high",
    custom_auth_mode: connections.custom?.auth_mode || value.custom_auth_mode || "none",
    custom_auth_header: connections.custom?.auth_header || value.custom_auth_header || "Authorization",
    custom_send_effort: value.custom_send_effort || false,
  });
  const [openaiKey, setOpenaiKey] = useState("");
  const [customAuthValue, setCustomAuthValue] = useState("");
  const [clearOpenaiKey, setClearOpenaiKey] = useState(false);
  const [clearCustomAuth, setClearCustomAuth] = useState(false);
  useEffect(() => {
    setConnection((current) => ({
      ...current,
      active_provider: connections.active_provider || current.active_provider,
      openai_model: connections.openai?.model ?? current.openai_model,
      gateway_url: connections.custom?.endpoint ?? current.gateway_url,
      gateway_model: connections.custom?.model ?? current.gateway_model,
      custom_auth_mode: connections.custom?.auth_mode ?? current.custom_auth_mode,
      custom_auth_header: connections.custom?.auth_header ?? current.custom_auth_header,
    }));
  }, [connections]);
  const put = (key: string, v: unknown) => setForm({ ...form, [key]: v });
  const putConnection = (key: string, v: unknown) =>
    setConnection({ ...connection, [key]: v });
  const activeConnection = connections[connection.active_provider] || {};
  const fields: [string, string, number, number?][] = [
    ["max_active_jobs", "Số job đồng thời", 1, 3],
    ["max_ai_calls", "Số lượt AI đồng thời", 1, 3],
    ["max_opus_calls", "Số lượt Opus đồng thời", 1, 1],
    ["attempt_timeout", "Giới hạn mỗi lượt giải (giây)", 1],
    ["scan_interval", "Chu kỳ quét (giây)", 0.1],
    ["stable_seconds", "Chờ nguồn ổn định (giây)", 0.1],
    ["retry_seconds", "Chờ thử lại lỗi vận hành (giây)", 1],
    ["output_timeout", "Giới hạn ghi output (giây)", 1],
    ["shutdown_seconds", "Thời gian chờ tắt (giây)", 1],
  ];
  return (
    <form
      className="settings"
      onSubmit={(e) => {
        e.preventDefault();
        const {
          active_provider: _activeProvider,
          openai_model: _openaiModel,
          gateway_url: _gatewayUrl,
          gateway_model: _gatewayModel,
          gateway_effort: _gatewayEffort,
          custom_auth_mode: _customAuthMode,
          custom_auth_header: _customAuthHeader,
          custom_send_effort: _customSendEffort,
          ...generalSettings
        } = form;
        save({
          ...generalSettings,
          roots: roots
            .split("\n")
            .map((r: string) => r.trim())
            .filter(Boolean),
        });
      }}
    >
      <section className="panel form-section">
        <h2>Nguồn bản vẽ & đầu ra</h2>
        <p>
          Mỗi thư mục job chứa trọn bộ PDF và DATA DXF. Job mới chỉ chạy khi anh
          chọn.
        </p>
        <label>
          Thư mục nguồn LAN
          <textarea
            aria-label="Thư mục nguồn LAN"
            rows={4}
            placeholder={"\\\\server\\banve\nD:\\CongViec"}
            value={roots}
            onChange={(e) => setRoots(e.target.value)}
          />
        </label>
        <small>
          Mỗi dòng một thư mục gốc. Dùng UNC hoặc ổ đĩa tài khoản Windows hiện
          tại đọc được.
        </small>
        <label>
          Thư mục workspace chung
          <input
            value={form.workspace_root || ""}
            placeholder="Đường dẫn tuyệt đối, ví dụ D:\\AI-Workspace"
            onChange={(e) => put("workspace_root", e.target.value)}
          />
        </label>
        <small>
          Mỗi lượt chạy mới lưu dữ liệu xử lý trong work/&lt;run-id&gt; và bản nguồn
          cố định trong cache/. Lượt chạy đang có giữ nguyên vị trí cũ.
        </small>
        <label className="review">
          <input
            type="checkbox"
            checked={form.individual_output || false}
            onChange={(e) => put("individual_output", e.target.checked)}
          />
          Xuất DXF riêng cho mã PASS
        </label>
        <label>
          Đích DXF riêng (để trống dùng parts_dxf trong job)
          <input
            value={form.individual_destination || ""}
            onChange={(e) =>
              put("individual_destination", e.target.value || null)
            }
          />
        </label>
        <label>
          Thư mục xuất DXF tổng (để trống = thư mục input của job)
          <input
            value={form.output_destination || ""}
            placeholder="Đường dẫn tuyệt đối, ví dụ D:\DXF-OUT"
            onChange={(e) => put("output_destination", e.target.value || null)}
          />
        </label>
        <label className="review">
          <input
            type="checkbox"
            checked={form.salvage_export ?? true}
            onChange={(e) => put("salvage_export", e.target.checked)}
          />
          Job dừng giữa chừng vẫn xuất DXF REVIEW ONLY từ các mã đã chốt
        </label>
        <label className="review">
          <input
            type="checkbox"
            checked={form.write_evidence ?? true}
            onChange={(e) => put("write_evidence", e.target.checked)}
          />
          Ghi JSON từng mã vào thư mục evidence/ cạnh DXF tổng
        </label>
        <label className="review">
          <input
            type="checkbox"
            checked={form.answer_by_ref || false}
            onChange={(e) => put("answer_by_ref", e.target.checked)}
          />
          Cho phép AI trả part_ref thay vì chép lại cả JSON (thử nghiệm, tắt mặc định)
        </label>
        <label className="review">
          <input
            type="checkbox"
            checked={form.effort_by_difficulty || false}
            onChange={(e) => put("effort_by_difficulty", e.target.checked)}
          />
          Mã khó chạy hội thoại riêng với effort cao hơn (thử nghiệm, tắt mặc định)
        </label>
        <label className="review">
          <input
            type="checkbox"
            checked={form.repo_generators || false}
            onChange={(e) => put("repo_generators", e.target.checked)}
          />
          Cho AI gọi bộ sinh BOXMET của repo (thử nghiệm, tắt mặc định)
        </label>
        <label className="review">
          <input
            type="checkbox"
            checked={form.precrop_views || false}
            onChange={(e) => put("precrop_views", e.target.checked)}
          />
          Cắt sẵn ảnh từng hình chiếu của mã gửi kèm lúc giải (thử nghiệm, tắt mặc định)
        </label>
        <label>
          Kiểu chạy (thử nghiệm)
          <select
            value={form.run_mode || "host"}
            onChange={(e) => put("run_mode", e.target.value)}
          >
            <option value="host">host điều khiển (mặc định)</option>
            <option value="agent">agent chạy script của app (thử nghiệm)</option>
          </select>
        </label>

      </section>
      <section className="panel form-section">
        <h2>Điều phối & ngân sách</h2>
        <div className="form-grid">
          {fields.map(([key, title, min, max]) => (
            <label key={key}>
              {title}
              <input
                type="number"
                required
                step="any"
                min={min}
                max={max}
                value={form[key] ?? ""}
                onChange={(e) => put(key, Number(e.target.value))}
              />
            </label>
          ))}
        </div>
        <p className="muted">
          Tối đa hai lượt giải mỗi mã trong cùng hội thoại. Không có lượt QA bằng AI riêng.
        </p>
      </section>
      <section className="panel form-section">
        <h2>Kết nối AI</h2>
        <p>Chọn tài khoản hoặc endpoint dùng cho các job mới. Khóa API được mã hóa riêng trên máy này.</p>
        <label>
          Nhà cung cấp
          <select
            value={connection.active_provider}
            onChange={(e) => putConnection("active_provider", e.target.value)}
          >
            <option value="claude">Claude · tài khoản Claude Code</option>
            <option value="openai">GPT · OpenAI API key</option>
            <option value="custom">Custom endpoint · OpenAI compatible</option>
          </select>
        </label>
        {connection.active_provider === "claude" && (
          <div className="form-section">
            <p>Phiên Claude: {providers.claude?.status === "ready" ? "Đã đăng nhập" : providers.claude?.status || "Chưa kiểm tra"}</p>
            {providers.claude?.message && <p className="muted">{providers.claude.message}</p>}
            <p>Yêu cầu thử: {connections.claude?.status === "ready" ? `Thành công với ${connections.claude.model}` : connections.claude?.status === "not_tested" ? "Chưa thử" : connections.claude?.status || "Chưa thử"}</p>
            {connections.claude?.message && <p className="muted">{connections.claude.message}</p>}
            <p className="muted">Dùng tài khoản Claude Code đã đăng nhập trên Windows này.</p>
            <div className="actions">
              {providers.claude?.status !== "ready" && (
                <button type="button" disabled={busy} onClick={loginClaude}>Đăng nhập Claude</button>
              )}
              <button type="button" disabled={busy} onClick={() => testConnection("claude")}>Kiểm tra kết nối</button>
            </div>
          </div>
        )}
        {connection.active_provider === "openai" && (
          <>
            <p className="muted">
              Dùng OpenAI API. Gói ChatGPT và API có thanh toán riêng. {" "}
              <a href="https://platform.openai.com/api-keys" target="_blank" rel="noreferrer">Tạo API key</a>
            </p>
            <label>
              Model
              <input
                value={connection.openai_model}
                placeholder="Model ID trong OpenAI API"
                onChange={(e) => putConnection("openai_model", e.target.value)}
              />
            </label>
            <label>
              OpenAI API key
              <input
                type="password"
                autoComplete="new-password"
                value={openaiKey}
                placeholder={connections.openai?.credential_configured ? "Đã lưu · để trống để giữ key hiện tại" : "Dán API key"}
                onChange={(e) => { setOpenaiKey(e.target.value); setClearOpenaiKey(false); }}
              />
            </label>
            {connections.openai?.credential_configured && (
              <button type="button" disabled={busy} onClick={() => { setOpenaiKey(""); setClearOpenaiKey(true); }}>
                Xóa key đã lưu
              </button>
            )}
          </>
        )}
        {connection.active_provider === "custom" && (
          <>
            <label>
              Base URL
              <input
                type="text"
                value={connection.gateway_url}
                placeholder="http://localhost:20128/v1"
                onChange={(e) => putConnection("gateway_url", e.target.value)}
              />
            </label>
            <label>
              Model ID
              <input
                value={connection.gateway_model}
                placeholder="provider/model-id"
                onChange={(e) => putConnection("gateway_model", e.target.value)}
              />
            </label>
            <label>
              Xác thực
              <select
                value={connection.custom_auth_mode}
                onChange={(e) => putConnection("custom_auth_mode", e.target.value)}
              >
                <option value="none">Không xác thực</option>
                <option value="bearer">Bearer API key</option>
                <option value="header">Header tùy chỉnh</option>
              </select>
            </label>
            {connection.custom_auth_mode === "header" && (
              <label>
                Tên auth header
                <input
                  value={connection.custom_auth_header}
                  placeholder="Authorization"
                  onChange={(e) => putConnection("custom_auth_header", e.target.value)}
                />
              </label>
            )}
            {connection.custom_auth_mode !== "none" && (
              <label>
                {connection.custom_auth_mode === "bearer" ? "API key" : "Giá trị auth header"}
                <input
                  type="password"
                  autoComplete="new-password"
                  value={customAuthValue}
                  placeholder={connections.custom?.credential_configured ? "Đã lưu · để trống để giữ giá trị hiện tại" : "Dán key hoặc giá trị header"}
                  onChange={(e) => { setCustomAuthValue(e.target.value); setClearCustomAuth(false); }}
                />
              </label>
            )}
            {connections.custom?.credential_configured && (
              <button type="button" disabled={busy} onClick={() => { setCustomAuthValue(""); setClearCustomAuth(true); }}>
                Xóa thông tin xác thực đã lưu
              </button>
            )}
            <label className="review">
              <input
                type="checkbox"
                checked={connection.custom_send_effort}
                onChange={(e) => putConnection("custom_send_effort", e.target.checked)}
              />
              Gửi tham số reasoning effort cho endpoint
            </label>
            <p className="muted">Base URL kết thúc ở /v1; app tự gọi /chat/completions. Kiểm tra kết nối gửi một yêu cầu ngắn đến model.</p>
          </>
        )}
        <div className="actions">
          <button
            type="button"
            className="primary"
            disabled={busy}
            onClick={() => saveConnection({
              ...connection,
              openai_api_key: openaiKey || undefined,
              custom_auth_value: customAuthValue || undefined,
              clear_openai_key: clearOpenaiKey,
              clear_custom_auth: clearCustomAuth,
            })}
          >
            Lưu & kiểm tra kết nối
          </button>
          {connection.active_provider !== "claude" && (
            <button type="button" disabled={busy} onClick={() => testConnection(connection.active_provider)}>
              Kiểm tra cấu hình đã lưu
            </button>
          )}
        </div>
        <p className="muted">
          Đang chọn: {connections.active_provider === "openai" ? "GPT" : connections.active_provider === "custom" ? "Custom endpoint" : "Claude"}
        </p>
        {activeConnection.status && <p>Trạng thái kết nối: {activeConnection.status}</p>}
      </section>
      <section className="panel form-section">
        <h2>Một agent cho mỗi job</h2>
        <p>Giữ cùng model và hội thoại từ đọc nguồn đến xuất DXF. Agent tự rà soát, công cụ local kiểm tra hình học và file xuất.</p>
        <div className="form-grid">
          <label>Model Claude
            <select value={form.agent_model || "sonnet-5.5"} onChange={(e) => put("agent_model", e.target.value)}>
              {["haiku-5.5", "sonnet-5.5", "opus-5.5"].map(m => <option key={m}>{m}</option>)}
            </select>
          </label>
          <label>Mức suy luận Claude
            <select value={form.agent_effort || "medium"} onChange={(e) => put("agent_effort", e.target.value)}>
              <option value="medium">Vừa · tiết kiệm</option>
              <option value="high">Cao</option>
              <option value="xhigh">Rất cao</option>
              <option value="max">Tối đa</option>
            </select>
          </label>
        </div>
        <p>GPT và Custom dùng model đã chọn trong Kết nối AI. Không tự chuyển model giữa job.</p>
      </section>
      <button className="primary" disabled={busy}>
        Lưu cài đặt
      </button>
    </form>
  );
}
