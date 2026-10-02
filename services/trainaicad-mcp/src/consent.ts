import { randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import type { AuthConfig } from "./auth.js";
const require = createRequire(import.meta.url);
export const supabaseBrowserScript = () =>
  readFileSync(
    join(
      dirname(require.resolve("@supabase/supabase-js/package.json")),
      "dist/umd/supabase.js",
    ),
  );
export function consentPage(config: AuthConfig) {
  const nonce = randomBytes(18).toString("base64");
  const publicConfig = JSON.stringify({
    project: config.issuer!.replace(/\/auth\/v1$/, ""),
    key: config.publishableKey,
    owner: config.ownerId,
    client: config.clientId,
    redirects: config.redirects,
  }).replace(/</g, "\\u003c");
  const html = `<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kết nối TrainAiCad</title>
<style nonce="${nonce}">body{font:16px system-ui;background:#f3f5f7;color:#18202a;margin:0}main{max-width:460px;margin:8vh auto;padding:28px;background:white;border-radius:16px}label{display:block;margin:14px 0}input{display:block;box-sizing:border-box;width:100%;padding:12px;margin-top:6px;border:1px solid #bbb;border-radius:6px}button{padding:12px 18px;margin:8px 8px 0 0;cursor:pointer}#message{white-space:pre-wrap}small{color:#536171}</style>
<main><h1>Kết nối TrainAiCad</h1><p>Dùng tài khoản CAD đã tạo trong Supabase.</p><form id="login"><label>Email<input id="email" type="email" autocomplete="username" required></label><label>Mật khẩu<input id="password" type="password" autocomplete="current-password" required></label><button>Đăng nhập</button></form>
<section id="consent" hidden><p id="client"></p><p>Cho phép đọc bản vẽ bạn chọn, lưu hồ sơ CAD và tạo/tải DXF để kiểm tra.</p><p><strong>DXF hiện là REVIEW ONLY / NO CUT.</strong></p><small id="scope"></small><p><button id="approve">Cho phép</button><button id="deny">Từ chối</button></p></section><p id="message" role="status"></p></main>
<script nonce="${nonce}" src="/oauth/supabase.js"></script><script nonce="${nonce}">
const cfg=${publicConfig}, $=id=>document.getElementById(id);
const auth=supabase.createClient(cfg.project,cfg.key,{auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}}).auth;
const id=new URL(location.href).searchParams.get('authorization_id');
function redirect(raw){const u=new URL(raw);const base=u.origin+u.pathname;if(!cfg.redirects.includes(base)||u.hash)throw Error('Callback không đúng cấu hình.');location.assign(u.href);}
async function details(){const {data,error}=await auth.oauth.getAuthorizationDetails(id);if(error)throw error;if(data.redirect_url){redirect(data.redirect_url);return;}
if(data.client.id!==cfg.client||!cfg.redirects.includes(data.redirect_uri)||data.user.id!==cfg.owner)throw Error('Tài khoản hoặc ứng dụng không được cấp quyền.');
$('login').hidden=true;$('consent').hidden=false;$('client').textContent='Ứng dụng: '+data.client.name;$('scope').textContent='Quyền OAuth: '+data.scope;$('message').textContent='';}
$('login').addEventListener('submit',async e=>{e.preventDefault();$('message').textContent='Đang đăng nhập…';try{if(!id||id.length>256)throw Error('Thiếu yêu cầu cấp quyền. Hãy kết nối lại từ ChatGPT.');const {data,error}=await auth.signInWithPassword({email:$('email').value,password:$('password').value});$('password').value='';if(error)throw Error('Đăng nhập không thành công.');if(data.user.id!==cfg.owner)throw Error('Tài khoản không được cấp quyền.');await details();}catch(e){$('password').value='';$('message').textContent=e.message;}});
for(const action of ['approve','deny'])$(action).onclick=async()=>{for(const a of ['approve','deny'])$(a).disabled=true;try{const fn=action==='approve'?'approveAuthorization':'denyAuthorization';const {data,error}=await auth.oauth[fn](id,{skipBrowserRedirect:true});if(error)throw error;redirect(data.redirect_url);}catch(e){$('message').textContent=e.message;for(const a of ['approve','deny'])$(a).disabled=false;}};
</script></html>`;
  return new Response(html, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "referrer-policy": "no-referrer",
      "x-content-type-options": "nosniff",
      "content-security-policy": `default-src 'none'; script-src 'self' 'nonce-${nonce}'; style-src 'nonce-${nonce}'; connect-src ${config.issuer!.replace(/\/auth\/v1$/, "")}; frame-ancestors 'none'; base-uri 'none'; form-action 'none'`,
    },
  });
}
