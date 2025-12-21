import Link from 'next/link';
import { badge, card, heading } from '@sakhi/ui';

// Legacy landing page retained for reference.
export default function LegacyHomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center gap-8 px-6 py-16">
      <section className={`${card} w-full p-10`}>
        <span className={badge({ variant: 'outline' })}>Monorepo</span>
        <h1 className={`mt-4 text-4xl ${heading}`}>Welcome to Sakhi on the Web</h1>
        <p className="mt-4 text-lg text-slate-600">
          This Next.js app is the foundation for the full web experience—perfect for SEO, rich dashboards, and
          marketing funnels while the Expo app continues to power iOS and Android.
        </p>
        <Link
          href="/journal"
          className="mt-6 inline-flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-md transition hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2"
        >
          Preview the journal screen →
        </Link>
      </section>

      <div className="grid w-full gap-6 md:grid-cols-2">
        <section className={`${card} p-8`}>
          <h2 className={`text-2xl ${heading}`}>Next Steps</h2>
          <ul className="mt-4 list-disc space-y-2 pl-4 text-slate-600">
            <li>Wire up Supabase auth and API clients shared with the mobile app.</li>
            <li>Port marketing pages and SEO-dependent flows here.</li>
            <li>Build dashboards and growth funnels tailored for desktop.</li>
          </ul>
        </section>

        <section className={`${card} p-8`}>
          <h2 className={`text-2xl ${heading}`}>Sharing Strategy</h2>
          <p className="mt-4 text-slate-600">
            Share logic via <code className="rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-800">packages/api</code>{' '}
            and component tokens via <code className="rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-800">packages/config</code>.
            UI can stay independent for now—upgrade to Tamagui or RN-web when parity matters.
          </p>
        </section>
      </div>
    </main>
  );
}
