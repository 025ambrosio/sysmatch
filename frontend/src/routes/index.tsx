import { useEffect, useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowRight, CheckCircle2, FileText, Percent, Tags } from "lucide-react";
import { MetricCard } from "@/components/MetricCard";
import { MARKETPLACES } from "@/lib/marketplaces";
import { listarLotes, type LoteResponse } from "@/lib/api";
import { totalPendencias } from "@/lib/loteStatus";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard geral - Conciliador NF x Etiquetas" },
      { name: "description", content: "Visão geral de conciliação por marketplace." },
    ],
  }),
  component: DashboardGeral,
});

function DashboardGeral() {
  const [lotes, setLotes] = useState<LoteResponse[]>([]);
  const [filtro, setFiltro] = useState<string>("todos");

  useEffect(() => {
    listarLotes().then(setLotes).catch(() => setLotes([]));
  }, []);

  const marketplacesAtivos = MARKETPLACES.map((marketplace) => marketplace.name);
  const lotesAtivos = lotes.filter((lote) => marketplacesAtivos.includes(lote.marketplace));
  const filtrados = useMemo(
    () => (filtro === "todos" ? lotesAtivos : lotesAtivos.filter((lote) => lote.marketplace === filtro)),
    [lotesAtivos, filtro],
  );

  const totais = useMemo(() => {
    return filtrados.reduce(
      (acc, lote) => ({
        notas: acc.notas + lote.totals.notas_lidas,
        etiquetas: acc.etiquetas + lote.totals.etiquetas_lidas,
        conciliadas: acc.conciliadas + lote.totals.conciliadas,
        pendentes: acc.pendentes + totalPendencias(lote),
      }),
      { notas: 0, etiquetas: 0, conciliadas: 0, pendentes: 0 },
    );
  }, [filtrados]);

  const taxa = totais.notas ? Math.round((totais.conciliadas / totais.notas) * 100) : 0;

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard geral</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Conciliação consolidada dos marketplaces ativos.
          </p>
        </div>
        <select
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
        >
          <option value="todos">Todos os marketplaces</option>
          {MARKETPLACES.map((marketplace) => (
            <option key={marketplace.slug} value={marketplace.name}>{marketplace.name}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="NFs lidas" value={totais.notas} icon={<FileText className="h-5 w-5" />} tone="info" />
        <MetricCard label="Etiquetas lidas" value={totais.etiquetas} icon={<Tags className="h-5 w-5" />} tone="info" />
        <MetricCard label="Conciliadas" value={totais.conciliadas} icon={<CheckCircle2 className="h-5 w-5" />} tone="success" />
        <MetricCard label="Taxa de conciliação" value={`${taxa}%`} icon={<Percent className="h-5 w-5" />} tone="success" />
        <MetricCard label="Pendências" value={totais.pendentes} icon={<AlertTriangle className="h-5 w-5" />} tone="warning" />
        <MetricCard label="Lotes" value={filtrados.length} tone="default" />
      </div>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Acessar marketplace
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {MARKETPLACES.map((marketplace) => {
            const lotesMarketplace = lotesAtivos.filter((lote) => lote.marketplace === marketplace.name);
            const conciliadas = lotesMarketplace.reduce((acc, lote) => acc + lote.totals.conciliadas, 0);
            const pendencias = lotesMarketplace.reduce((acc, lote) => acc + totalPendencias(lote), 0);
            const Icon = marketplace.icon;
            return (
              <Link
                key={marketplace.slug}
                to="/marketplace/$slug"
                params={{ slug: marketplace.slug }}
                className="group flex flex-col gap-3 rounded-xl border bg-card p-5 shadow-sm transition-colors hover:border-primary"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`flex h-10 w-10 items-center justify-center rounded-lg ${marketplace.color} text-white`}>
                      <Icon className="h-5 w-5" />
                    </span>
                    <div>
                      <h3 className="text-base font-semibold">{marketplace.name}</h3>
                      <p className="text-xs text-muted-foreground">{lotesMarketplace.length} lote(s)</p>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Conciliadas</p>
                    <p className="text-lg font-semibold text-success">{conciliadas}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Pendências</p>
                    <p className="text-lg font-semibold text-warning">{pendencias}</p>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
