import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { useLoad } from "../util";
import Modal from "../components/Modal";
import StateBox from "../components/StateBox";

export default function Autoreplies() {
  const { t } = useI18n();
  const { data, loading, error, reload, setData } = useLoad(() => api("/bot/rules"), []);
  const [adding, setAdding] = useState(false);

  const toggle = async (rule) => {
    const updated = await api(`/bot/rules/${rule.id}`, { method: "PATCH", body: { active: !rule.active } });
    setData((list) => list.map((r) => (r.id === rule.id ? updated : r)));
  };

  const remove = async (rule) => {
    await api(`/bot/rules/${rule.id}`, { method: "DELETE" });
    setData((list) => list.filter((r) => r.id !== rule.id));
  };

  return (
    <div className="page narrow">
      <header className="page-head">
        <div>
          <h1>{t.nav.bot}</h1>
          <p>{t.bot.intro}</p>
        </div>
        <button className="btn primary" onClick={() => setAdding(true)}>
          <Plus size={17} />
          {t.bot.add}
        </button>
      </header>

      <StateBox loading={loading} error={error} onRetry={reload}>
        {data && data.length === 0 ? (
          <p className="state">{t.bot.empty}</p>
        ) : (
          <ul className="rules">
            {data?.map((rule) => (
              <li key={rule.id} className={rule.active ? "rule" : "rule off"}>
                <div className="rule-body">
                  <span className="keyword">{rule.keyword}</span>
                  <p>{rule.reply}</p>
                </div>
                <label className="switch" title={t.bot.on}>
                  <input type="checkbox" checked={rule.active} onChange={() => toggle(rule)} aria-label={t.bot.on} />
                  <span />
                </label>
                <button className="icon-btn" onClick={() => remove(rule)} aria-label={t.bot.delete} title={t.bot.delete}>
                  <Trash2 size={17} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </StateBox>

      {adding && (
        <NewRule
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false);
            reload();
          }}
        />
      )}
    </div>
  );
}

function NewRule({ onClose, onSaved }) {
  const { t } = useI18n();
  const [keyword, setKeyword] = useState("");
  const [reply, setReply] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/bot/rules", { method: "POST", body: { keyword, reply } });
      onSaved();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <Modal title={t.bot.newTitle} onClose={onClose}>
      <form onSubmit={submit}>
        <label className="field">
          <span>{t.bot.keyword}</span>
          <input value={keyword} onChange={(e) => setKeyword(e.target.value)} required autoFocus maxLength={80} />
          <small>{t.bot.keywordHint}</small>
        </label>
        <label className="field">
          <span>{t.bot.reply}</span>
          <textarea value={reply} onChange={(e) => setReply(e.target.value)} required rows={4} maxLength={1000} />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="btn ghost" onClick={onClose}>{t.common.cancel}</button>
          <button className="btn primary" disabled={busy}>{t.bot.save}</button>
        </div>
      </form>
    </Modal>
  );
}
