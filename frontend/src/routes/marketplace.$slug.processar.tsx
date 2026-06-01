import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Loader2, Play, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { FileDropzone } from "@/components/FileDropzone";
import { ResultadoView } from "@/components/ResultadoView";
import { findMarketplace } from "@/lib/marketplaces";
import { listarLotes, processarLote, type LoteResponse } from "@/lib/api";

export const Route = createFileRoute("/marketplace/$slug/processar")({
  component: Processar,
});

const NF_EXTENSIONS = [".pdf", ".xml", ".zip"];
const LABEL_EXTENSIONS = [".pdf", ".zpl", ".txt", ".png", ".jpg", ".jpeg", ".zip"];

function fileExt(file: File) {
  const dot = file.name.lastIndexOf(".");
  return dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
}

function invalidFiles(files: File[], allowed: string[]) {
  return files.filter((file) => !allowed.includes(fileExt(file)));
}

function Processar() {
  const { slug } = Route.useParams();
  const m = findMarketplace(slug)!;
  const [nfs, setNfs] = useState<File[]>([]);
  const [etqs, setEtqs] = useState<File[]>([]);
  const [batchName, setBatchName] = useState("");
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<LoteResponse | null>(null);

  const resetBatch = () => {
    setNfs([]);
    setEtqs([]);
    setBatchName("");
    setResultado(null);
  };

  const validateBeforeProcess = async () => {
    if (!m?.name) return "Selecione um marketplace antes de processar.";
    if (nfs.length === 0) return "Envie pelo menos um arquivo de NF/DANFE antes de processar.";
    if (etqs.length === 0) return "Envie pelo menos um arquivo de etiqueta antes de processar.";

    const badNfs = invalidFiles(nfs, NF_EXTENSIONS);
    if (badNfs.length) return "Formato de NF/DANFE não aceito. Use PDF, XML ou ZIP.";

    const badLabels = invalidFiles(etqs, LABEL_EXTENSIONS);
    if (badLabels.length) return "Formato de etiqueta não aceito. Use PDF, ZIP, ZPL, TXT, PNG ou JPG.";

    if (batchName.trim()) {
      const existing = await listarLotes(m.name).catch(() => []);
      const duplicate = existing.some(
        (lote) => (lote.batch_name ?? "").trim().toLowerCase() === batchName.trim().toLowerCase(),
      );
      if (duplicate) return "Já existe um lote com esse nome. Escolha outro nome ou deixe o campo em branco.";
    }

    const max = Math.max(nfs.length, etqs.length);
    const min = Math.min(nfs.length, etqs.length);
    if (max >= 4 && min > 0 && max / min >= 3) {
      return "A quantidade de NFs e etiquetas está muito divergente. Confira os arquivos antes de processar.";
    }

    return "";
  };

  const onProcess = async () => {
    const error = await validateBeforeProcess();
    if (error) {
      toast.error("Revise os arquivos", { description: error });
      return;
    }

    setLoading(true);
    setResultado(null);
    try {
      const lote = await processarLote(nfs, etqs, {
        marketplace: m.name,
        batchName: batchName || undefined,
      });
      setResultado(lote);
      const pendencias = lote.totals.etiquetas_sem_nf + lote.totals.notas_sem_etiqueta + lote.totals.para_revisar;
      toast.success(pendencias > 0 ? "Processado com pendências" : "Processamento concluído", {
        description: `${lote.totals.conciliadas} conciliada(s), ${pendencias} pendência(s).`,
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
        <h2 className="text-lg font-semibold">Novo processamento - {m.name}</h2>
        <p className="text-sm text-muted-foreground">
          Siga os passos para conciliar notas fiscais e etiquetas deste lote.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <StepCard step="1" title="Enviar arquivos de NF/DANFE">
          <FileDropzone
            title="Notas fiscais / DANFEs"
            description="Envie XMLs de NF-e, PDFs de DANFE ou ZIP."
            accept=".pdf,.xml,.zip"
            acceptedTypes={["PDF", "XML", "ZIP"]}
            files={nfs}
            onFilesChange={setNfs}
          />
        </StepCard>

        <StepCard step="2" title="Enviar etiquetas">
          <FileDropzone
            title={`Etiquetas ${m.name}`}
            description={`Envie etiquetas geradas no ${m.name}.`}
            accept=".pdf,.zpl,.txt,.png,.jpg,.jpeg,.zip"
            acceptedTypes={["PDF", "ZIP", "ZPL", "TXT", "PNG", "JPG"]}
            files={etqs}
            onFilesChange={setEtqs}
          />
        </StepCard>
      </div>

      <section className="rounded-xl border bg-card p-5">
        <div className="grid gap-4 md:grid-cols-[1fr_auto_auto] md:items-end">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Passo 3 - Nome do lote (opcional)
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
            className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-primary px-6 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {loading ? "Processando arquivos..." : "Processar arquivos"}
          </button>
          <button
            type="button"
            onClick={resetBatch}
            disabled={loading}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-input bg-background px-4 text-sm font-medium hover:bg-muted disabled:opacity-60"
          >
            <RotateCcw className="h-4 w-4" />
            Limpar
          </button>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          {nfs.length} arquivo(s) de NF · {etqs.length} arquivo(s) de etiqueta
        </p>
      </section>

      {loading && (
        <div className="rounded-xl border bg-card p-8 text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
          <p className="mt-3 text-sm font-medium">Processando arquivos...</p>
          <p className="text-xs text-muted-foreground">Aguarde enquanto o lote de {m.name} é conciliado.</p>
        </div>
      )}

      {resultado && <ResultadoView lote={resultado} onNewBatch={resetBatch} />}
    </div>
  );
}

function StepCard({ step, title, children }: { step: string; title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
          {step}
        </span>
        <h3 className="text-sm font-semibold">{title}</h3>
      </div>
      {children}
    </section>
  );
}
