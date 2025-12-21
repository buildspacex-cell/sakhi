export default function LegacyLandingPage() {
  return (
    <main
      className="min-h-screen w-full flex items-center justify-center px-6 py-16"
      style={{ backgroundColor: "#0e0f12", color: "#f4f4f5" }}
    >
      <section className="w-full max-w-3xl text-center space-y-8">
        <div className="text-sm uppercase tracking-[0.12em] text-[#a1a1aa]">Sakhi</div>

        <h1 className="text-3xl sm:text-[28px] font-medium leading-snug">This is not a chatbot.</h1>

        <p className="text-lg sm:text-xl leading-relaxed text-[#e5e7eb]">
          Sakhi is a reflective intelligence that learns how a person operates over time.
          <br />
          <br />
          What you’re about to see is how understanding forms — from raw human input to a living personal model.
        </p>

        <div className="flex justify-center">
          <a
            href="/journal"
            className="inline-flex items-center justify-center px-8 py-3 rounded-full border border-[#e5e7eb] text-base tracking-wide hover:bg-[#f4f4f5] hover:text-[#0e0f12] transition-colors duration-200"
          >
            Begin
          </a>
        </div>
      </section>
    </main>
  );
}
