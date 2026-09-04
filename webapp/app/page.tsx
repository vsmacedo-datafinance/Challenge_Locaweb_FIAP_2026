import { headers } from "next/headers";
import DashboardShell from "@/components/DashboardShell";
import Topbar from "@/components/Topbar";
import type { DashboardResponse } from "@/lib/types";

async function getDashboard(): Promise<DashboardResponse> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("host") ?? "localhost:3000";
  const protocol = host.startsWith("localhost") || host.startsWith("127.0.0.1") ? "http" : "https";

  const res = await fetch(`${protocol}://${host}/api/dashboard`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Falha ao carregar /api/dashboard (${res.status})`);
  }
  return res.json();
}

export default async function Page() {
  const data = await getDashboard();

  return (
    <main className="min-h-screen">
      <Topbar updatedAtLabel={data.updated_at_label} />
      <DashboardShell data={data} />
    </main>
  );
}
