type EventRecord = Record<string, any>;
type EventPage = {events?: EventRecord[]; next_after?: number; run_id?: string | null};

export async function loadEvents(
  api: (url: string) => Promise<EventPage>,
  jobId: string,
  current: () => boolean = () => true,
  initialRunId: string | null = null,
): Promise<EventRecord[]> {
  const events: EventRecord[] = [];
  let after = 0;
  let runId: string | null = initialRunId;
  while (current()) {
    const query = runId ? `?after=${after}&run_id=${encodeURIComponent(runId!)}` : '';
    const page = await api(`/api/jobs/${encodeURIComponent(jobId)}/events${query}`);
    if (!current()) return [];
    const rows = page.events || [];
    if (!rows.length) break;
    if (runId && page.run_id !== runId) throw Error('Phiên hoạt động đã thay đổi');
    runId = page.run_id || null;
    events.push(...rows);
    const next = page.next_after;
    if (!runId || next == null || next <= after) break;
    after = next;
  }
  return events;
}
