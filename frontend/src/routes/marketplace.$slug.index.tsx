import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { FileText, Tags, CheckCircle2, Percent, AlertTriangle, Plus } from "lucide-react";
import { MetricCard } from "@/components/MetricCard";
import { findMarketplace } from "@/lib/marketplaces";
import { listarLotes, type LoteResponse } from "@/lib/api";

export const Route = createFileRoute("/marketplace/$slug/")({
  component: MarketplaceDashboard,
});

function MarketplaceDashboard() {
  const { slug } = Route.useParams();
  const m = findMarketplace(slug)!;
  const [lotes, setLotes] = useState<LoteResponse[]>([]);

  useEffect(() => {
    listarLotes(m.name).then(setLotes).catch(() => setLotes([]));
  }, [m.name]);

  const totais = lotes.reduce(
    (acc, l) => ({
      notas: acc.notas + l.totals.notas_lidas,
      etiquetas: acc.etiquetas + l.totals.etiquetas_lidas,
      conciliadas: acc.conciliadas + l.totals.conciliadas,
      pendentes:
        acc.pendentes + l.totals.etiquetas_sem_nf + l.totals.notas_sem_etiqueta + l.totals.para_revisar,
    }),
    { notas: 0, etiquetas: 0, conciliadas: 0, pendentes: 0 },
  );
  const taxa = totais.notas ? Math.round((totais.conciliadas / totais.notas) * 100) : 0;

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 p-6 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Visão geral · {m.name}</h2>
          <p className="text-sm text-muted-foreground">
            Somatório dos lotes processados para {m.name}.
          </p>
        </div>
        <Link
          to="/marketplace/$slug/processar"
          params={{ slug }}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          Novo processamento
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="NFs lidas" value={totais.notas} icon={<FileText className="h-5 w-5" />} tone="info" />
        <MetricCard label="Etiquetas lidas" value={totais.etiquetas} icon={<Tags className="h-5 w-5" />} tone="info" />
        <MetricCard label="Conciliadas" value={totais.conciliadas} icon={<CheckCircle2 className="h-5 w-5" />} tone="success" />
        <MetricCard label="Taxa de conciliação" value={`${taxa}%`} icon={<Percent className="h-5 w-5" />} tone="success" />
        <MetricCard label="Pendências" value={totais.pendentes} icon={<AlertTriangle className="h-5 w-5" />} tone="warning" />
        <MetricCard label="Lotes processados" value={lotes.length} tone="default" />
      </div>

      <section className="rounded-xl border bg-card">
        <header className="flex items-center justify-between border-b px-5 py-4">
          <div>
            <h3 className="text-base font-semibold">Lotes recentes</h3>
            <p className="text-xs text-muted-foreground">Últimos processamentos de {m.name}.</p>
          </div>
          <Link
            to="/marketplace/$slug/historico"
            params={{ slug }}
            className="text-sm font-medium text-primary hover:underline"
          >
            Ver histórico
          </Link>
        </header>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-5 py-3">Lote</th>
                <th className="px-5 py-3">Nome</th>
                <th className="px-5 py-3 text-right">NFs</th>
                <th className="px-5 py-3 text-right">Etiquetas</th>
                <th className="px-5 py-3 text-right">Conciliadas</th>
                <th className="px-5 py-3 text-right">Pendências</th>
              </tr>
            </thead>
            <tbody>
              {lotes.slice(0, 8).map((l) => (
                <tr key={l.job_id} className="border-t hover:bg-muted/30">
                  <td className="px-5 py-3 font-mono text-xs text-muted-foreground">{l.job_id}</td>
                  <td className="px-5 py-3 font-medium">{l.batch_name ?? "—"}</td>
                  <td className="px-5 py-3 text-right tabular-nums">{l.totals.notas_lidas}</td>
                  <td className="px-5 py-3 text-right tabular-nums">{l.totals.etiquetas_lidas}</td>
                  <td className="px-5 py-3 text-right tabular-nums text-success">{l.totals.conciliadas}</td>
                  <td className="px-5 py-3 text-right tabular-nums text-warning">
                    {l.totals.etiquetas_sem_nf + l.totals.notas_sem_etiqueta + l.totals.para_revisar}
                  </td>
                </tr>
              ))}
              {lotes.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-10 text-center text-sm text-muted-foreground">
                    Nenhum lote processado ainda para {m.name}.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
