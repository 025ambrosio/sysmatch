import { createFileRoute, Link, Outlet, useRouterState, notFound } from "@tanstack/react-router";
import { LayoutDashboard, FilePlus2, History, AlertTriangle } from "lucide-react";
import { findMarketplace } from "@/lib/marketplaces";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/marketplace/$slug")({
  beforeLoad: ({ params }) => {
    if (!findMarketplace(params.slug)) throw notFound();
  },
  head: ({ params }) => {
    const m = findMarketplace(params.slug);
    return {
      meta: [
        { title: `${m?.name ?? "Marketplace"} · Conciliador NF x Etiquetas` },
        { name: "description", content: `Conciliação NF x etiquetas — ${m?.name ?? ""}` },
      ],
    };
  },
  component: MarketplaceLayout,
});

function MarketplaceLayout() {
  const { slug } = Route.useParams();
  const m = findMarketplace(slug)!;
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const base = `/marketplace/${slug}`;
  const Icon = m.icon;

  const tabs = [
    { url: base, label: "Dashboard", icon: LayoutDashboard, exact: true },
    { url: `${base}/processar`, label: "Novo processamento", icon: FilePlus2 },
    { url: `${base}/historico`, label: "Histórico", icon: History },
    { url: `${base}/pendencias`, label: "Pendências", icon: AlertTriangle },
  ];

  return (
    <div className="flex min-h-full flex-col">
      <div className="border-b bg-card">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-6 py-5 lg:px-8">
          <span className={`flex h-12 w-12 items-center justify-center rounded-xl ${m.color} text-white shadow-sm`}>
            <Icon className="h-6 w-6" />
          </span>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Marketplace</p>
            <h1 className="text-xl font-semibold tracking-tight">{m.name}</h1>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4 lg:px-6">
          {tabs.map((t) => {
            const active = t.exact ? pathname === t.url : pathname === t.url || pathname.startsWith(t.url + "/");
            return (
              <Link
                key={t.url}
                to={t.url}
                className={cn(
                  "inline-flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "border-primary text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground",
                )}
              >
                <t.icon className="h-4 w-4" />
                {t.label}
              </Link>
            );
          })}
        </nav>
      </div>
      <Outlet />
    </div>
  );
}
