-- Run ONLY in a dedicated TrainAiCad Supabase project, after replacing all 3 values.
-- If this project already has a Custom Access Token Hook, integrate this logic into
-- the existing hook instead of selecting/replacing it blindly.
create or replace function public.trainaicad_access_token_hook(event jsonb)
returns jsonb language plpgsql stable
set search_path = ''
as $$
declare
  claims jsonb := event->'claims';
  cad_client text := 'R27cf2045-0476-4279-aa30-7107059471a4';
  cad_owner text := '572cbd8a-75b5-41b2-8f44-1a68fc9fc4f8';
  cad_resource text := 'https://trainaicad.onrender.com/mcp';
begin
  if cad_client like 'REPLACE_%' or cad_owner like 'REPLACE_%' or cad_resource like 'REPLACE_%' then
    raise exception 'TrainAiCad OAuth hook is not configured';
  end if;
  -- Preserve other sessions and other clients. Only the pinned owner/client gets CAD access.
  if claims->>'client_id' = cad_client and claims->>'sub' = cad_owner then
    claims := jsonb_set(claims, '{aud}', to_jsonb(cad_resource));
    claims := jsonb_set(claims, '{scope}', to_jsonb('openid'::text));
    claims := jsonb_set(claims, '{trainaicad_access}', 'true'::jsonb);
  end if;
  return jsonb_build_object('claims', claims);
end;
$$;
grant usage on schema public to supabase_auth_admin;
grant execute on function public.trainaicad_access_token_hook(jsonb) to supabase_auth_admin;
revoke execute on function public.trainaicad_access_token_hook(jsonb) from anon, authenticated, public;
-- Dashboard: Authentication > Hooks > Custom Access Token > select this function.
-- Use an ES256/RS256 asymmetric Auth signing key; the MCP server rejects HS256.
