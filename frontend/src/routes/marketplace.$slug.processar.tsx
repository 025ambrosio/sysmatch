import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { FileDropzone } from "@/components/FileDropzone";
import { ResultadoView } from "@/components/ResultadoView";
import { findMarketplace } from "@/lib/marketplaces";
import { processarLote, type LoteResponse } from "@/lib/api";

export const Route = createFileRoute("/marketplace/$slug/processar")({
  component: Processar,
});

function Processar() {
  const { slug } = Route.useParams();
  const m = findMarketplace(slug)!;
  const [nfs, setNfs] = useState<File[]>([]);
  const [etqs, setEtqs] = useState<File[]>([]);
  const [batchName, setBatchName] = useState("");
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<LoteResponse | null>(null);

  const onProcess = async () => {
    if (nfs.length === 0 && etqs.length === 0) {
      toast.message("Modo demo", { description: "Nenhum arquivo enviado — gerando lote de exemplo." });
    }
    setLoading(true);
    setResultado(null);
    try {
      const lote = await processarLote(nfs, etqs, {
        marketplace: m.name,
        batchName: batchName || undefined,
      });
      setResultado(lote);
      toast.success("Lote processado", {
        description: `${lote.totals.conciliadas} de ${lote.totals.notas_lidas} NFs conciliadas`,
      });
    } catch (e: any) {
      toast.error("Erro ao processar", { description: e?.message ?? "Tente novamente." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 p-6 lg:p-8">
      <div>
        <h2 className="text-lg font-semibold">Novo processamento — {m.name}</h2>
        <p className="text-sm text-muted-foreground">
          Envie as NFs/DANFEs e as etiquetas para conciliar este lote de {m.name}.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <FileDropzone
          title="Notas fiscais / DANFEs"
          description="Envie XMLs de NF-e ou PDFs de DANFE."
          accept=".pdf,.xml,.zip"
          acceptedTypes={["PDF", "XML", "ZIP"]}
          files={nfs}
          onFilesChange={setNfs}
        />
        <FileDropzone
          title={`Etiquetas ${m.name}`}
          description={`Envie etiquetas geradas no ${m.name}.`}
          accept=".pdf,.zpl,.png,.jpg,.jpeg,.zip"
          acceptedTypes={["PDF", "ZPL", "PNG", "JPG", "ZIP"]}
          files={etqs}
          onFilesChange={setEtqs}
        />
      </div>

      <section className="rounded-xl border bg-card p-5">
        <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Nome do lote (opcional)
            </span>
            <input
              value={batchName}
              onChange={(e) => setBatchName(e.target.value)}
              placeholder={`Ex.: Lote manhã ${m.name}`}
              className="w-full rounded-md border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </label>
          <button
            type="button"
            onClick={onProcess}
            disabled={loading}
            className="inline-flex h-11 items-center gap-2 rounded-md bg-primary px-6 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {loading ? "Processando..." : "Processar arquivos"}
          </button>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          {nfs.length} arquivo(s) de NF · {etqs.length} arquivo(s) de etiqueta
        </p>
      </section>

      {loading && (
        <div className="rounded-xl border bg-card p-8 text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
          <p className="mt-3 text-sm font-medium">Processando lote de {m.name}…</p>
          <p className="text-xs text-muted-foreground">Isso pode levar alguns segundos.</p>
        </div>
      )}

      {resultado && <ResultadoView lote={resultado} />}
    </div>
  );
}
