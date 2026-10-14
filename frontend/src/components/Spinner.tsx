export default function Spinner({ dark }: { dark?: boolean }) {
  return (
    <span
      className={`spinner-animated ${dark ? "spinner-dark" : ""}`}
      aria-label="Loading"
      role="status"
    />
  );
}
