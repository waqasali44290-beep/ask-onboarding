// Round avatar with a person's initials, or the assistant's sparkle.
const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]!.toUpperCase())
    .join("");

export default function Avatar({ name, assistant = false }: { name: string; assistant?: boolean }) {
  return (
    <span className={`avatar${assistant ? " avatar-assistant" : ""}`} aria-hidden="true">
      {assistant ? "✦" : initials(name)}
    </span>
  );
}
