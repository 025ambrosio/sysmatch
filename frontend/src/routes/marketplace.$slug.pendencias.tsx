import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { ResultadoView } from "@/components/ResultadoView";
import { findMarketplace } from "@/lib/marketplaces";
import { getLote, listarLotes, type LoteResponse } from "@/lib/api";

export const Route = createFileRoute("/marketplace/$slug/pendencias")({
  component: Pendencias,
});

function Pendencias() {
  const { slug } = Route.useParams();
  const m = findMarketplace(slug)!;
  const [lotes, setLotes] = useState<LoteResponse[]>([]);
  const [selecionado, setSelecionado] = useState<LoteResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listarLotes(m.name).then(async (lista) => {
      setLotes(lista);
      if (lista[0]) {
        const detail = (await getLote(lista[0].job_id)) ?? lista[0];
        setSelecionado(detail);
      }
      setLoading(false);
    });
  }, [m.name]);

  const onSelect = async (id: string) => {
    const detail = await getLote(id);
    if (detail) setSelecionado(detail);
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 p-6 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Verificar pendências - {m.name}</h2>
          <p className="text-sm text-muted-foreground">
            Revise conciliados, etiquetas sem NF, NFs sem etiqueta e itens para revisar.
          </p>
        </div>
        {lotes.length > 0 && (
          <select
            value={selecionado?.job_id ?? ""}
            onChange={(e) => onSelect(e.target.value)}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          >
            {lotes.map((lote) => (
              <option key={lote.job_id} value={lote.job_id}>
                {lote.batch_name ?? lote.job_id}
              </option>
            ))}
          </select>
        )}
      </div>

      {loading && (
        <div className="rounded-xl border bg-card p-10 text-center text-sm text-muted-foreground">
          Carregando...
        </div>
      )}

      {!loading && !selecionado && (
        <div className="rounded-xl border bg-card p-10 text-center text-sm text-muted-foreground">
          Nenhum lote processado ainda para {m.name}. Vá em "Novo processamento" para começar.
        </div>
      )}

      {selecionado && <ResultadoView lote={selecionado} />}
    </div>
  );
}
