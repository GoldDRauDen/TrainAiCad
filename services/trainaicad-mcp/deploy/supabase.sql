-- Dedicated private bucket. Run in the user's own project.
insert into storage.buckets (id,name,public)
values ('trainaicad-private','trainaicad-private',false)
on conflict (id) do nothing;
-- Backend service_role access only; no anon/public storage policies.
