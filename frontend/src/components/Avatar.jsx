import { initials } from "../util";

const tones = ["tone-a", "tone-b", "tone-c", "tone-d"];

export default function Avatar({ name, size = "md" }) {
  const tone = tones[[...name].reduce((sum, ch) => sum + ch.charCodeAt(0), 0) % tones.length];
  return (
    <span className={`avatar ${size} ${tone}`} aria-hidden="true">
      {initials(name)}
    </span>
  );
}
