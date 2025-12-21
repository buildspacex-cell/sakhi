import Link from 'next/link';

const items = [
  'Sakhi does not decide for you.',
  'You can leave or pause at any point.',
  'No profiling. No persuasion.',
  'This is a reflective space only.',
];

export default function ContractPage() {
  return (
    <main
      className="min-h-screen w-full flex items-center justify-center px-6 py-16"
      style={{ backgroundColor: '#F6F4F0', color: '#2F2F2F' }}
    >
      <section className="w-full max-w-xl space-y-10 text-left">
        <div className="space-y-4">
          <h1 className="text-3xl font-light tracking-tight">Relationship contract</h1>
          <ul className="space-y-2 text-sm" style={{ color: '#2F2F2F' }}>
            {items.map((line) => (
              <li key={line} className="leading-relaxed">
                {line}
              </li>
            ))}
          </ul>
        </div>

        <div className="flex items-center">
          <Link
            href="/calibration"
            className="border border-black/10 text-sm font-medium px-6 py-2 rounded-sm hover:opacity-80 focus:outline-none focus:ring-0"
            aria-label="Continue to calibration"
          >
            Continue
          </Link>
        </div>
      </section>
    </main>
  );
}
