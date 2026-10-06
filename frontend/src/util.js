import { useCallback, useEffect, useRef, useState } from "react";

export function useLoad(loader, deps = [], every = 0) {
  const [state, setState] = useState({ data: null, error: "", loading: true });
  const loaderRef = useRef(loader);
  const ticket = useRef(0);
  loaderRef.current = loader;

  const run = useCallback(async () => {
    const mine = ++ticket.current;
    try {
      const data = await loaderRef.current();
      if (mine === ticket.current) setState({ data, error: "", loading: false });
    } catch (e) {
      if (mine === ticket.current) setState((s) => ({ ...s, error: e.message, loading: false }));
    }
  }, []);

  useEffect(() => {
    run();
    if (!every) return undefined;
    const id = setInterval(run, every);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, every, run]);

  const setData = useCallback(
    (next) => setState((s) => ({ ...s, data: typeof next === "function" ? next(s.data) : next })),
    []
  );

  return { ...state, reload: run, setData };
}

export function useDebounced(value, delay = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

const locale = (lang) => (lang === "hi" ? "hi-IN" : "en-IN");

export const money = (amount, lang) =>
  new Intl.NumberFormat(locale(lang), {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);

export const clock = (iso, lang) =>
  new Date(iso).toLocaleTimeString(locale(lang), { hour: "numeric", minute: "2-digit" });

export const shortDate = (iso, lang) =>
  new Date(iso).toLocaleDateString(locale(lang), { day: "numeric", month: "short" });

export const weekday = (isoDate, lang) =>
  new Date(`${isoDate}T12:00:00`).toLocaleDateString(locale(lang), { weekday: "short" });

const dayKey = (d) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;

export function dayLabel(iso, lang, t) {
  const date = new Date(iso);
  const now = new Date();
  const yesterday = new Date();
  yesterday.setDate(now.getDate() - 1);
  if (dayKey(date) === dayKey(now)) return t.today;
  if (dayKey(date) === dayKey(yesterday)) return t.yesterday;
  return date.toLocaleDateString(locale(lang), { day: "numeric", month: "long", year: "numeric" });
}

export function listTime(iso, lang, t) {
  const date = new Date(iso);
  const now = new Date();
  const yesterday = new Date();
  yesterday.setDate(now.getDate() - 1);
  if (dayKey(date) === dayKey(now)) return clock(iso, lang);
  if (dayKey(date) === dayKey(yesterday)) return t.yesterday;
  return shortDate(iso, lang);
}

export function sameDay(a, b) {
  return dayKey(new Date(a)) === dayKey(new Date(b));
}

export function formatPhone(phone) {
  if (phone.startsWith("+91") && phone.length === 13) {
    return `+91 ${phone.slice(3, 8)} ${phone.slice(8)}`;
  }
  return phone;
}

export const initials = (name) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
