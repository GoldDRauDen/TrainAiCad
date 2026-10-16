import React from "react";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "../src/App";
const writes: { url: string; body: unknown; token: unknown }[] = [];
beforeEach(() => {
  writes.length = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, options?: RequestInit) => {
      if (options?.method) {
        writes.push({
          url,
          body: JSON.parse(String(options.body)),
          token: (options.headers as Record<string, string>)["X-Luan-Token"],
        });
      }
      const data =
        url === "/api/health"
          ? { mutation_token: "session", active_jobs: 0, active_ai_calls: 0 }
          : url === "/api/providers"
            ? {
                claude: { status: "unavailable" },
                gateway: { status: "not_selected" },
              }
            : url === "/api/settings"
              ? {
                  roots: [],
                  max_opus_calls: 1,
                  attempt_timeout: 1200,
                  scan_interval: 5,
                  stable_seconds: 10,
                  retry_seconds: 60,
                  output_timeout: 120,
                  shutdown_seconds: 10,
                  gateway_url: "http://localhost:20128/v1",
                  models: { easy: { model: "haiku-5.5", effort: "medium" } },
                  max_active_jobs: 3,
                  max_ai_calls: 2,
                }
              : url === "/api/jobs"
                ? {
                    jobs: [
                      {
                        id: "job1",
                        display_name: "520318-15",
                        folder: "C:/jobs/520318-15",
                        status: "discovered",
                        technical_counts: {},
                        usage: {},
                        durations: {},
                      },
                    ],
                  }
                : {};
      return { ok: true, json: async () => data };
    }),
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
test("selects discovered job and starts only selected IDs with session token", async () => {
  render(<App />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole("checkbox", { name: /520318-15/ }));
  await user.click(screen.getByRole("button", { name: /Chạy đã chọn/ }));
  await waitFor(() =>
    expect(
      writes.some(
        (w) => w.url === "/api/jobs/job1/start" && w.token === "session",
      ),
    ).toBe(true),
  );
});
test("settings saves LAN roots and displays backend errors", async () => {
  render(<App />);
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Cài đặt" }));
  const roots = await screen.findByLabelText("Thư mục nguồn LAN");
  await user.type(roots, "C:/jobs");
  await user.click(screen.getByRole("button", { name: "Lưu cài đặt" }));
  await waitFor(() =>
    expect(
      writes.some(
        (w) =>
          w.url === "/api/settings" &&
          (w.body as { roots: string[] }).roots[0] === "C:/jobs",
      ),
    ).toBe(true),
  );
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: false,
      json: async () => ({ error: { message: "LAN chưa kết nối" } }),
    })),
  );
  await user.click(screen.getByRole("button", { name: "Lưu cài đặt" }));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    expect.stringContaining("LAN chưa kết nối"),
  );
});
