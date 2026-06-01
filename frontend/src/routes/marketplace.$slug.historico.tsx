import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { FileDown, FileSpreadsheet, Archive } from "lucide-react";
import { findMarketplace } from "@/lib/marketplaces";
import { downloadUrls, listarLotes, type LoteResponse } from "@/lib/api";

export const Route = createFileRoute("/marketplace/$slug/historico")({
  component: Historico,
});

function Historico() {
  const { slug } = Route.useParams();
  const m = findMarketplace(slug)!;
  const [lotes, setLotes] = useState<LoteResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listarLotes(m.name)
      .then((l) => setLotes(l))
      .catch((e) => setErro(e?.message ?? "Erro ao carregar histórico"))
      .finally(() => setLoading(false));
  }, [m.name]);

  return (
    <div className="mx-auto w-full max-w-7xl space-y-4 p-6 lg:p-8">
      <div>
        <h2 className="text-lg font-semibold">Histórico — {m.name}</h2>
        <p className="text-sm text-muted-foreground">Todos os lotes processados para {m.name}.</p>
      </div>

      {erro && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {erro}
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-5 py-3">Lote</th>
              <th className="px-5 py-3">Nome</th>
              <th className="px-5 py-3">Marketplace</th>
              <th className="px-5 py-3 text-right">NFs</th>
              <th className="px-5 py-3 text-right">Etiquetas</th>
              <th className="px-5 py-3 text-right">Conciliadas</th>
              <th className="px-5 py-3 text-right">Pendências</th>
              <th className="px-5 py-3 text-right">Downloads</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={8} className="px-5 py-10 text-center text-sm text-muted-foreground">
                  Carregando…
                </td>
              </tr>
            )}
            {!loading && lotes.length === 0 && (
              <tr>
                <td colSpan={8} className="px-5 py-10 text-center text-sm text-muted-foreground">
                  Nenhum lote processado ainda para {m.name}.
                </td>
              </tr>
            )}
            {lotes.map((l) => {
              const u = downloadUrls(l.job_id);
              const pend = l.totals.etiquetas_sem_nf + l.totals.notas_sem_etiqueta + l.totals.para_revisar;
              return (
                <tr key={l.job_id} className="border-t hover:bg-muted/30">
                  <td className="px-5 py-3 font-mono text-xs text-muted-foreground">{l.job_id}</td>
                  <td className="px-5 py-3 font-medium">{l.batch_name ?? "—"}</td>
                  <td className="px-5 py-3">{l.marketplace}</td>
                  <td className="px-5 py-3 text-right tabular-nums">{l.totals.notas_lidas}</td>
                  <td className="px-5 py-3 text-right tabular-nums">{l.totals.etiquetas_lidas}</td>
                  <td className="px-5 py-3 text-right tabular-nums text-success">{l.totals.conciliadas}</td>
                  <td className="px-5 py-3 text-right tabular-nums text-warning">{pend}</td>
                  <td className="px-5 py-3">
                    <div className="flex justify-end gap-1">
                      <a href={u.pdfFinal} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-muted" title="PDF final">
                        <FileDown className="h-3.5 w-3.5" />
                      </a>
                      <a href={u.excel} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-muted" title="Excel">
                        <FileSpreadsheet className="h-3.5 w-3.5" />
                      </a>
                      <a href={u.zipIndividuais} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-muted" title="ZIP individuais">
                        <Archive className="h-3.5 w-3.5" />
                      </a>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
