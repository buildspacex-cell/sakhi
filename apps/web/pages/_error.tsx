/**
 * Custom error page — replaces Next.js default which uses styled-jsx
 * (styled-jsx causes useContext crash in monorepos with multiple React versions)
 */
import type { NextPageContext } from "next";

function ErrorPage({ statusCode }: { statusCode?: number }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        fontFamily: "system-ui, -apple-system, sans-serif",
        background: "#0a0a0a",
        color: "#ededed",
      }}
    >
      <h1 style={{ fontSize: "2rem", fontWeight: 700, margin: 0 }}>
        {statusCode || "Error"}
      </h1>
      <p style={{ color: "#888", marginTop: "0.5rem" }}>
        {statusCode === 404
          ? "This page could not be found."
          : "An unexpected error occurred."}
      </p>
    </div>
  );
}

ErrorPage.getInitialProps = ({ res, err }: NextPageContext) => {
  const statusCode = res ? res.statusCode : err ? err.statusCode : 404;
  return { statusCode };
};

export default ErrorPage;
