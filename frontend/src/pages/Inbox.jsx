import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, CheckCheck, MessageSquarePlus, Search, Send } from "lucide-react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { clock, dayLabel, formatPhone, listTime, sameDay, useDebounced, useLoad } from "../util";
import Avatar from "../components/Avatar";
import Modal from "../components/Modal";

export default function Inbox() {
  const { id } = useParams();
  const { t, lang } = useI18n();
  const [query, setQuery] = useState("");
  const [state, setState] = useState("all");
  const [simulating, setSimulating] = useState(false);
  const navigate = useNavigate();
  const q = useDebounced(query);

  const list = useLoad(
    () => api(`/conversations?state=${state}&q=${encodeURIComponent(q)}`),
    [state, q],
    8000
  );
  const conversations = list.data || [];

  return (
    <div className={`inbox ${id ? "has-chat" : ""}`}>
      <section className="inbox-list">
        <div className="inbox-top">
          <div className="inbox-title">
            <h1>{t.nav.inbox}</h1>
            <button className="btn ghost small" onClick={() => setSimulating(true)}>
              <MessageSquarePlus size={15} />
              {t.inbox.simulate}
            </button>
          </div>
          <label className="search">
            <Search size={17} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t.inbox.searchPlaceholder} />
          </label>
          <div className="tabs" role="tablist">
            {["all", "open", "resolved"].map((key) => (
              <button
                key={key}
                role="tab"
                aria-selected={state === key}
                className={state === key ? "tab on" : "tab"}
                onClick={() => setState(key)}
              >
                {key === "all" ? t.common.all : t.inbox[key]}
              </button>
            ))}
          </div>
        </div>

        <ul className="convo-list">
          {conversations.map((c) => (
            <li key={c.id}>
              <Link to={`/inbox/${c.id}`} className={`convo ${String(c.id) === id ? "on" : ""}`}>
                <Avatar name={c.customer.name} />
                <div className="convo-body">
                  <div className="convo-line">
                    <b>{c.customer.name}</b>
                    <time>{listTime(c.last_message_at, lang, t.inbox)}</time>
                  </div>
                  <div className="convo-line">
                    <span className="preview">{c.preview || formatPhone(c.customer.phone)}</span>
                    {c.unread > 0 && <span className="badge">{c.unread}</span>}
                  </div>
                </div>
              </Link>
            </li>
          ))}
          {!list.loading && conversations.length === 0 && (
            <li className="state">{q ? t.common.nothingFound : t.inbox.noChats}</li>
          )}
        </ul>
      </section>

      {simulating && (
        <SimulateModal
          onClose={() => setSimulating(false)}
          onSent={(conversationId) => {
            setSimulating(false);
            list.reload();
            navigate(`/inbox/${conversationId}`);
          }}
        />
      )}

      {id ? (
        <ChatPane key={id} id={id} onChanged={list.reload} />
      ) : (
        <section className="chat empty-chat">
          <p>{t.inbox.pick}</p>
        </section>
      )}
    </div>
  );
}

function ChatPane({ id, onChanged }) {
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const { data, error, setData, reload } = useLoad(() => api(`/conversations/${id}`), [id], 5000);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const bottom = useRef(null);
  const count = data?.messages.length ?? 0;

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [count]);

  const send = async (e) => {
    e.preventDefault();
    const body = text.trim();
    if (!body || sending) return;
    setSending(true);
    setSendError("");
    try {
      const message = await api(`/conversations/${id}/messages`, { method: "POST", body: { body } });
      setData((d) => ({ ...d, status: "open", messages: [...d.messages, message] }));
      setText("");
      onChanged();
    } catch (err) {
      setSendError(err.message);
    } finally {
      setSending(false);
    }
  };

  const toggleStatus = async () => {
    const next = data.status === "open" ? "resolved" : "open";
    await api(`/conversations/${id}`, { method: "PATCH", body: { status: next } });
    setData((d) => ({ ...d, status: next }));
    onChanged();
  };

  if (error && !data) {
    return (
      <section className="chat empty-chat">
        <p>{error}</p>
        <button className="btn ghost" onClick={reload}>{t.common.retry}</button>
      </section>
    );
  }
  if (!data) {
    return <section className="chat empty-chat"><p>{t.common.loading}</p></section>;
  }

  return (
    <section className="chat">
      <header className="chat-head">
        <button className="icon-btn back" onClick={() => navigate("/inbox")} aria-label="Back">
          <ArrowLeft size={20} />
        </button>
        <Avatar name={data.customer.name} />
        <div className="chat-who">
          <b>{data.customer.name}</b>
          <small>{formatPhone(data.customer.phone)}</small>
        </div>
        <button className="btn ghost" onClick={toggleStatus}>
          {data.status === "open" ? t.inbox.markResolved : t.inbox.reopen}
        </button>
      </header>

      <div className="messages">
        {data.messages.length === 0 && <p className="state">{t.inbox.noMessages}</p>}
        {data.messages.map((m, i) => {
          const prev = data.messages[i - 1];
          return (
            <div key={m.id} className="msg-row">
              {(!prev || !sameDay(prev.created_at, m.created_at)) && (
                <div className="day">{dayLabel(m.created_at, lang, t.inbox)}</div>
              )}
              <div className={`bubble ${m.direction === "out" ? "mine" : "theirs"} ${m.source === "bot" ? "bot" : ""}`}>
                <p>{m.body}</p>
                <span className="meta">
                  {clock(m.created_at, lang)}
                  {m.direction === "out" && <Delivery status={m.status} />}
                </span>
              </div>
              {m.source === "bot" && <small className="delivery-note">{t.inbox.auto}</small>}
              {m.direction === "out" && (m.status === "queued" || m.status === "failed") && (
                <small className={`delivery-note ${m.status}`}>{t.inbox[m.status]}</small>
              )}
            </div>
          );
        })}
        <div ref={bottom} />
      </div>

      {data.customer.opted_out ? (
        <div className="composer"><p className="note">{t.inbox.optedOut}</p></div>
      ) : !data.window_open ? (
        <div className="composer">
          <p className="note">{t.inbox.windowClosed}</p>
          <TemplateSender
            conversationId={id}
            onSent={(message) => {
              setData((d) => ({ ...d, status: "open", messages: [...d.messages, message] }));
              onChanged();
            }}
          />
        </div>
      ) : (
        <form className="composer" onSubmit={send}>
          {sendError && <p className="form-error">{sendError}</p>}
          <div className="composer-row">
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder={t.inbox.write} aria-label={t.inbox.write} />
            <button className="btn primary" disabled={!text.trim() || sending}>
              <Send size={16} />
              {t.inbox.send}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

function Delivery({ status }) {
  if (status === "sent") return <Check size={14} />;
  if (status === "delivered") return <CheckCheck size={14} />;
  if (status === "read") return <CheckCheck size={14} className="read-tick" />;
  return null;
}

function TemplateSender({ conversationId, onSent }) {
  const { t } = useI18n();
  const templates = useLoad(() => api("/templates"), []);
  const [templateId, setTemplateId] = useState("");
  const [values, setValues] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const chosen = templates.data?.find((tpl) => String(tpl.id) === templateId);

  const choose = (id) => {
    setTemplateId(id);
    const tpl = templates.data?.find((x) => String(x.id) === id);
    setValues(Array(tpl ? tpl.variables : 0).fill(""));
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onSent(
        await api(`/conversations/${conversationId}/template`, {
          method: "POST",
          body: { template_id: Number(templateId), variables: values },
        })
      );
      setTemplateId("");
      setValues([]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (templates.data && templates.data.length === 0) return <p className="help">{t.inbox.noTemplates}</p>;

  return (
    <form className="template-sender" onSubmit={submit}>
      <select value={templateId} onChange={(e) => choose(e.target.value)} aria-label={t.inbox.template}>
        <option value="">{t.inbox.pickTemplate}</option>
        {templates.data?.map((tpl) => (
          <option key={tpl.id} value={tpl.id}>{tpl.name}</option>
        ))}
      </select>
      {chosen && (
        <>
          <p className="template-preview">{chosen.body}</p>
          {values.map((value, i) => (
            <input
              key={i}
              value={value}
              onChange={(e) => setValues(values.map((v, j) => (j === i ? e.target.value : v)))}
              placeholder={`${t.inbox.value} {{${i + 1}}}`}
              required
            />
          ))}
        </>
      )}
      {error && <p className="form-error">{error}</p>}
      <button className="btn primary" disabled={!chosen || busy}>
        <Send size={16} />
        {t.inbox.sendTemplate}
      </button>
    </form>
  );
}

function SimulateModal({ onClose, onSent }) {
  const { t } = useI18n();
  const customers = useLoad(() => api("/customers"), []);
  const [customerId, setCustomerId] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api("/demo/simulate", {
        method: "POST",
        body: { customer_id: Number(customerId), text },
      });
      onSent(result.conversation_id);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <Modal title={t.inbox.simulateTitle} onClose={onClose}>
      <form onSubmit={submit}>
        <p className="help">{t.inbox.simulateHelp}</p>
        <label className="field">
          <span>{t.inbox.customer}</span>
          <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
            <option value="">{t.orders.selectCustomer}</option>
            {customers.data?.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>{t.inbox.message}</span>
          <textarea value={text} onChange={(e) => setText(e.target.value)} required rows={3} maxLength={1000} />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="btn ghost" onClick={onClose}>{t.common.cancel}</button>
          <button className="btn primary" disabled={busy}>{t.inbox.simulateSend}</button>
        </div>
      </form>
    </Modal>
  );
}
