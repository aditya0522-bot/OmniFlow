import { useEffect, useState } from "react";
import { LogOut, Trash2 } from "lucide-react";
import { api, publicBase } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { clock, shortDate, useLoad } from "../util";
import StateBox from "../components/StateBox";

export default function Settings() {
  const { user, isAdmin, logout } = useAuth();
  const { t, lang, setLang } = useI18n();
  const config = useLoad(() => api("/public/config"), []);
  const [resetDone, setResetDone] = useState(false);

  const resetDemo = async () => {
    await api("/demo/reset", { method: "POST" });
    setResetDone(true);
    setTimeout(() => setResetDone(false), 2500);
  };

  return (
    <div className="page narrow">
      <header className="page-head">
        <div>
          <h1>{t.nav.settings}</h1>
          <p>{user.tenant.name}</p>
        </div>
      </header>

      <section className="panel">
        <div className="panel-head"><h2>{t.settings.account}</h2></div>
        <dl className="facts">
          <div><dt>{t.login.email}</dt><dd>{user.email}</dd></div>
          <div><dt>{t.settings.workspace}</dt><dd>{user.tenant.name}</dd></div>
          <div>
            <dt>{t.settings.language}</dt>
            <dd>
              <div className="tabs">
                <button className={lang === "en" ? "tab on" : "tab"} onClick={() => setLang("en")}>English</button>
                <button className={lang === "hi" ? "tab on" : "tab"} onClick={() => setLang("hi")}>हिन्दी</button>
              </div>
            </dd>
          </div>
        </dl>
        <button className="btn ghost mobile-only" onClick={logout}>
          <LogOut size={16} />
          {t.common.signOut}
        </button>
      </section>

      <PasswordForm />

      {isAdmin && <WhatsAppPanel />}
      {isAdmin && <TemplatesPanel />}
      {isAdmin && <AuditPanel />}

      {isAdmin && config.data?.demo_mode && (
        <section className="panel">
          <div className="panel-head"><h2>{t.settings.demoTitle}</h2></div>
          <p className="help">{t.settings.demoText}</p>
          <div className="form-foot">
            <button className="btn ghost" onClick={resetDemo}>{t.settings.demoReset}</button>
            {resetDone && <span className="saved">{t.settings.demoDone}</span>}
          </div>
        </section>
      )}
    </div>
  );
}

function PasswordForm() {
  const { t } = useI18n();
  const { changePassword } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await changePassword(current, next);
      setCurrent("");
      setNext("");
      setDone(true);
      setTimeout(() => setDone(false), 2500);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <section className="panel">
      <div className="panel-head"><h2>{t.settings.password}</h2></div>
      <form onSubmit={submit}>
        <label className="field">
          <span>{t.settings.currentPassword}</span>
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required autoComplete="current-password" />
        </label>
        <label className="field">
          <span>{t.settings.newPassword}</span>
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} required minLength={8} autoComplete="new-password" />
          <small>{t.login.passwordHint}</small>
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="form-foot">
          <button className="btn primary">{t.settings.updatePassword}</button>
          {done && <span className="saved">{t.settings.passwordChanged}</span>}
        </div>
      </form>
    </section>
  );
}

function WhatsAppPanel() {
  const { t } = useI18n();
  const { data, loading, error, reload, setData } = useLoad(() => api("/settings/whatsapp"), []);
  const [phoneId, setPhoneId] = useState("");
  const [token, setToken] = useState("");
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    if (data) setPhoneId((current) => current || data.phone_number_id);
  }, [data]);

  const save = async (body) => {
    setSaveError("");
    try {
      setData(await api("/settings/whatsapp", { method: "PUT", body }));
      setToken("");
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setSaveError(err.message);
    }
  };

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{t.settings.whatsapp}</h2>
        {data && (
          <span className={`pill ${data.connected ? "delivered" : "received"}`}>
            {data.connected ? t.settings.connected : t.settings.notConnected}
          </span>
        )}
      </div>

      <StateBox loading={loading} error={error} onRetry={reload}>
        {data && (
          <>
            <p className="help">{t.settings.help}</p>
            <dl className="facts">
              <div><dt>{t.settings.webhookUrl}</dt><dd><code>{publicBase}{data.webhook_path}</code></dd></div>
              <div><dt>{t.settings.verifyToken}</dt><dd><code>{data.verify_token}</code></dd></div>
            </dl>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                save({ phone_number_id: phoneId, access_token: token || null });
              }}
            >
              <label className="field">
                <span>{t.settings.phoneId}</span>
                <input value={phoneId} onChange={(e) => setPhoneId(e.target.value)} />
                <small>{t.settings.phoneIdHint}</small>
              </label>
              <label className="field">
                <span>{t.settings.tokenLabel}</span>
                <input
                  type="password"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  autoComplete="off"
                  placeholder={data.token_set ? "••••••••••••" : ""}
                />
                <small>{data.token_set ? t.settings.tokenSet : t.settings.tokenHint}</small>
              </label>
              {saveError && <p className="form-error" role="alert">{saveError}</p>}
              <div className="form-foot">
                <button className="btn primary">{t.common.save}</button>
                {data.token_set && (
                  <button type="button" className="btn ghost" onClick={() => save({ phone_number_id: phoneId, clear_token: true })}>
                    {t.settings.clearToken}
                  </button>
                )}
                {saved && <span className="saved">{t.common.saved}</span>}
              </div>
            </form>
          </>
        )}
      </StateBox>
    </section>
  );
}

function TemplatesPanel() {
  const { t } = useI18n();
  const { data, loading, error, reload, setData } = useLoad(() => api("/templates"), []);
  const [form, setForm] = useState({ name: "", language: "en", body: "" });
  const [formError, setFormError] = useState("");
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const add = async (e) => {
    e.preventDefault();
    setFormError("");
    try {
      const created = await api("/templates", { method: "POST", body: form });
      setData((list) => [...list, created]);
      setForm({ name: "", language: "en", body: "" });
    } catch (err) {
      setFormError(err.message);
    }
  };

  const remove = async (template) => {
    await api(`/templates/${template.id}`, { method: "DELETE" });
    setData((list) => list.filter((x) => x.id !== template.id));
  };

  return (
    <section className="panel">
      <div className="panel-head"><h2>{t.settings.templates}</h2></div>
      <p className="help">{t.settings.templatesHelp}</p>

      <StateBox loading={loading} error={error} onRetry={reload}>
        {data?.length > 0 && (
          <ul className="rules">
            {data.map((tpl) => (
              <li key={tpl.id} className="rule">
                <div className="rule-body">
                  <span className="keyword">{tpl.name} · {tpl.language}</span>
                  <p>{tpl.body}</p>
                </div>
                <button className="icon-btn" onClick={() => remove(tpl)} aria-label="Delete">
                  <Trash2 size={17} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </StateBox>

      <form onSubmit={add} className="template-form">
        <div className="two-col">
          <label className="field">
            <span>{t.settings.templateName}</span>
            <input value={form.name} onChange={set("name")} required pattern="[a-z0-9_]+" maxLength={80} placeholder="order_update" />
          </label>
          <label className="field">
            <span>{t.settings.templateLang}</span>
            <input value={form.language} onChange={set("language")} required pattern="[a-z]{2}(_[A-Z]{2})?" maxLength={10} />
          </label>
        </div>
        <label className="field">
          <span>{t.settings.templateBody}</span>
          <textarea value={form.body} onChange={set("body")} required rows={3} maxLength={1000} />
        </label>
        {formError && <p className="form-error" role="alert">{formError}</p>}
        <button className="btn primary">{t.settings.addTemplate}</button>
      </form>
    </section>
  );
}

function AuditPanel() {
  const { t, lang } = useI18n();
  const { data, loading, error, reload } = useLoad(() => api("/settings/audit"), []);
  return (
    <section className="panel">
      <div className="panel-head"><h2>{t.settings.audit}</h2></div>
      <StateBox loading={loading} error={error} onRetry={reload}>
        {data?.length === 0 ? (
          <p className="state">{t.settings.auditEmpty}</p>
        ) : (
          <ul className="audit">
            {data?.map((row) => (
              <li key={row.id}>
                <div>
                  <b>{row.user_name}</b> {row.action.replaceAll("_", " ")}
                  {row.detail && <small className="sub">{row.detail}</small>}
                </div>
                <time>{shortDate(row.created_at, lang)}, {clock(row.created_at, lang)}</time>
              </li>
            ))}
          </ul>
        )}
      </StateBox>
    </section>
  );
}
