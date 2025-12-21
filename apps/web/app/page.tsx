const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#e5e7eb",
};

export default function HomePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: palette.bg,
        color: palette.fg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 32px",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif',
      }}
    >
      <section style={{ maxWidth: "720px", textAlign: "center" }}>
        <div
          style={{
            fontSize: "16px",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: palette.muted,
            marginBottom: "32px",
          }}
        >
          Sakhi
        </div>

        <h1
          style={{
            fontSize: "26px",
            fontWeight: 500,
            lineHeight: 1.4,
            margin: "0 0 36px 0",
          }}
        >
          Who Sakhi is for — first
        </h1>

        <ul style={{ listStyle: "none", padding: 0, margin: "0 0 48px 0" }}>
          <li
            style={{
              fontSize: "18px",
              lineHeight: 1.6,
              color: palette.accent,
              marginBottom: "20px",
            }}
          >
            Thoughtful, high-responsibility professionals who feel mentally overloaded but care deeply about clarity.
          </li>
          <li
            style={{
              fontSize: "18px",
              lineHeight: 1.6,
              color: palette.accent,
              marginBottom: "20px",
            }}
          >
            Their weekly problem isn’t productivity — it’s losing clarity under sustained responsibility.
          </li>
          <li
            style={{
              fontSize: "18px",
              lineHeight: 1.6,
              color: palette.accent,
              marginBottom: 0,
            }}
          >
            Sakhi helps them see patterns in how they operate, so better decisions come naturally.
          </li>
        </ul>

        <a
          href="/landing"
          style={{
            display: "inline-block",
            padding: "14px 36px",
            borderRadius: "999px",
            border: `1px solid ${palette.accent}`,
            color: palette.fg,
            textDecoration: "none",
            fontSize: "15px",
            letterSpacing: "0.04em",
            transition: "background 0.25s ease, color 0.25s ease",
          }}
        >
          See how it works
        </a>
      </section>
    </main>
  );
}
