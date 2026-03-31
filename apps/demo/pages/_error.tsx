import type { NextPageContext } from "next";

function ErrorPage({ statusCode }: { statusCode?: number }) {
  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        background: "#0f1115",
        color: "#f8fafc",
        fontFamily: "Avenir Next, Segoe UI, sans-serif",
      }}
    >
      <h1 style={{ fontSize: "2rem", fontWeight: 700, margin: 0 }}>
        {statusCode || "Error"}
      </h1>
      <p style={{ color: "#94a3b8", marginTop: "0.5rem" }}>
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
