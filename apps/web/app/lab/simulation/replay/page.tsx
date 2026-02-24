export const dynamic = "force-dynamic";
export const revalidate = false;

import ReplayClient from "./ReplayClient";

export default function Page() {
  return <ReplayClient />;
}
