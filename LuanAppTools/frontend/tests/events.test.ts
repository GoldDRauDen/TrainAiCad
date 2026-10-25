import { expect, test } from 'vitest';
import { loadEvents } from '../src/events';
test('loads later pages from the same run beyond a thousand events', async () => {
  const pages = [
    {events: Array.from({length: 1000}, (_, i) => ({id: i + 1})), next_after: 1000, run_id: 'old'},
    {events: [{id: 1001, kind: 'latest'}], next_after: 1001, run_id: 'old'},
    {events: [], next_after: 1001, run_id: 'old'},
  ];
  const urls: string[] = [];
  const result = await loadEvents(async (url: string) => { urls.push(url); return pages.shift()!; }, 'job1');
  expect(result.at(-1)).toEqual({id: 1001, kind: 'latest'});
  expect(result).toHaveLength(1001);
  expect(urls[1]).toBe('/api/jobs/job1/events?after=1000&run_id=old');
});
test('stops when a newer refresh supersedes it', async () => {
  const result = await loadEvents(async () => ({events: [{id: 1}], next_after: 1, run_id: 'run1'}), 'job1', () => false);
  expect(result).toEqual([]);
});
test('pins the first page to the run displayed in job detail', async () => {
  const urls: string[] = [];
  await loadEvents(async (url: string) => { urls.push(url); return {events: [], next_after: 0, run_id: 'shown'}; }, 'job1', () => true, 'shown');
  expect(urls).toEqual(['/api/jobs/job1/events?after=0&run_id=shown']);
});
