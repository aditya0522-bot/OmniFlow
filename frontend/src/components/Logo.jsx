export default function Logo({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#ffffff" />
      <path
        d="M8 11.5A3.5 3.5 0 0 1 11.5 8h6A3.5 3.5 0 0 1 21 11.5v3a3.5 3.5 0 0 1-3.5 3.5H14l-3 2.6V18a3.5 3.5 0 0 1-3-3.5z"
        fill="#1f5bf0"
      />
      <path
        d="M24 14.5v4a3.5 3.5 0 0 1-3.5 3.5H19l-1.5 1.8"
        fill="none"
        stroke="#7fa3ff"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
