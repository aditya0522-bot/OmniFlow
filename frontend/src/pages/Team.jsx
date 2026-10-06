import { useState } from "react";
import { Plus } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { useLoad } from "../util";
import Avatar from "../components/Avatar";
import Modal from "../components/Modal";
import StateBox from "../components/StateBox";

export default function Team() {
  const { t } = useI18n();
  const { user } = useAuth();
  const { data, loading, error, reload, setData } = useLoad(() => api("/team"), []);
  const [adding, setAdding] = useState(false);
  const [resetting, setResetting] = useState(null);
  const [actionError, setActionError] = useState("");

  const patch = async (member, body) => {
    setActionError("");
    try {
      const updated = await api(`/team/${member.id}`, { method: "PATCH", body });
      setData((list) => list.map((m) => (m.id === member.id ? updated : m)));
    } catch (err) {
      setActionError(err.message);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>{t.nav.team}</h1>
          <p>{t.team.intro}</p>
        </div>
        <button className="btn primary" onClick={() => setAdding(true)}>
          <Plus size={17} />
          {t.team.add}
        </button>
      </header>

      {actionError && <p className="form-error" role="alert">{actionError}</p>}

      <StateBox loading={loading} error={error} onRetry={reload}>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>{t.team.name}</th>
                <th>{t.team.role}</th>
                <th>{t.team.status}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data?.map((m) => {
                const isMe = m.id === user.id;
                return (
                  <tr key={m.id}>
                    <td>
                      <div className="who">
                        <Avatar name={m.name} size="sm" />
                        <div>
                          <span className="strong">{m.name}{isMe && ` (${t.team.you})`}</span>
                          <small className="sub">{m.email}</small>
                        </div>
                      </div>
                    </td>
                    <td>
                      <select
                        className="plain-select"
                        value={m.role}
                        disabled={isMe}
                        onChange={(e) => patch(m, { role: e.target.value })}
                        aria-label={t.team.role}
                      >
                        <option value="admin">{t.team.admin}</option>
                        <option value="agent">{t.team.agent}</option>
                      </select>
                    </td>
                    <td>
                      <span className={`pill ${m.is_active ? "delivered" : "cancelled"}`}>
                        {m.is_active ? t.team.active : t.team.inactive}
                      </span>
                    </td>
                    <td className="actions">
                      <button className="btn ghost small" onClick={() => setResetting(m)}>{t.team.resetPassword}</button>{" "}
                      {!isMe && (
                        <button className="btn ghost small" onClick={() => patch(m, { is_active: !m.is_active })}>
                          {m.is_active ? t.team.deactivate : t.team.activate}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </StateBox>

      {adding && (
        <AddMember
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false);
            reload();
          }}
        />
      )}
      {resetting && (
        <ResetPassword
          member={resetting}
          onClose={() => setResetting(null)}
          onSave={async (password) => {
            await patch(resetting, { password });
            setResetting(null);
          }}
        />
      )}
    </div>
  );
}

function AddMember({ onClose, onSaved }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "agent" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/team", { method: "POST", body: form });
      onSaved();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <Modal title={t.team.newTitle} onClose={onClose}>
      <form onSubmit={submit}>
        <label className="field"><span>{t.team.name}</span><input value={form.name} onChange={set("name")} required autoFocus /></label>
        <label className="field"><span>{t.team.email}</span><input type="email" value={form.email} onChange={set("email")} required /></label>
        <label className="field"><span>{t.team.password}</span><input type="password" value={form.password} onChange={set("password")} required minLength={8} autoComplete="new-password" /><small>{t.login.passwordHint}</small></label>
        <label className="field">
          <span>{t.team.role}</span>
          <select value={form.role} onChange={set("role")}>
            <option value="agent">{t.team.agent}</option>
            <option value="admin">{t.team.admin}</option>
          </select>
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="btn ghost" onClick={onClose}>{t.common.cancel}</button>
          <button className="btn primary" disabled={busy}>{t.team.add}</button>
        </div>
      </form>
    </Modal>
  );
}

function ResetPassword({ member, onClose, onSave }) {
  const { t } = useI18n();
  const [password, setPassword] = useState("");
  return (
    <Modal title={`${t.team.resetPassword}: ${member.name}`} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSave(password);
        }}
      >
        <label className="field">
          <span>{t.team.newPassword}</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" autoFocus />
        </label>
        <div className="modal-actions">
          <button type="button" className="btn ghost" onClick={onClose}>{t.common.cancel}</button>
          <button className="btn primary">{t.team.save}</button>
        </div>
      </form>
    </Modal>
  );
}
