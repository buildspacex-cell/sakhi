import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import {
  MVP_PRESENTATION_ACCESS_COOKIE,
  getMvpPresentationAccessToken,
  isValidMvpPresentationAccessToken,
  matchesMvpPresentationPassword,
} from "@/lib/mvpPresentationAccess";

async function unlockPitch(formData: FormData) {
  "use server";

  const password = String(formData.get("password") || "").trim();

  if (!matchesMvpPresentationPassword(password)) {
    redirect("/pitch/unlock?error=1");
  }

  const accessToken = getMvpPresentationAccessToken();
  const cookieStore = await cookies();
  cookieStore.set(MVP_PRESENTATION_ACCESS_COOKIE, accessToken, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 14,
  });

  redirect("/pitch");
}

export default async function PitchUnlockPage({
  searchParams,
}: {
  searchParams?: {
    error?: string;
  };
}) {
  const cookieStore = await cookies();
  const hasAccess = isValidMvpPresentationAccessToken(
    cookieStore.get(MVP_PRESENTATION_ACCESS_COOKIE)?.value
  );

  if (hasAccess) {
    redirect("/pitch");
  }

  const showError = searchParams?.error === "1";

  return (
    <main className="min-h-screen bg-[#06101d] text-slate-50">
      <div className="mx-auto flex min-h-screen w-full max-w-3xl items-center justify-center px-6 py-16">
        <div className="w-full max-w-md rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,22,38,0.96),rgba(7,12,22,0.92))] p-10 shadow-[0_40px_120px_rgba(0,0,0,0.38)]">
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
            Sakhi
          </p>
          <h1 className="text-3xl font-semibold leading-tight text-white">
            Investor Pitch
          </h1>
          <p className="mt-4 text-base leading-7 text-slate-300">
            Enter the shared password to access the Sakhi investor pitch deck.
          </p>

          {showError ? (
            <div className="mt-6 rounded-2xl border border-rose-300/20 bg-rose-200/10 px-4 py-3 text-sm leading-6 text-rose-100">
              That password is incorrect.
            </div>
          ) : null}

          <form action={unlockPitch} className="mt-8 space-y-4">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-300">
                Password
              </span>
              <input
                type="password"
                name="password"
                autoComplete="current-password"
                className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white outline-none transition focus:border-[#e5d1a0]/40 focus:bg-white/8"
                placeholder="Enter password"
              />
            </label>
            <button
              type="submit"
              className="w-full rounded-2xl bg-[#e5d1a0] px-4 py-3 text-base font-semibold text-slate-950 transition hover:bg-[#eddcb4] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Open pitch deck
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}
