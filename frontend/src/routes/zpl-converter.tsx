import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Clipboard, Download, FileText, Loader2, Play, RotateCcw, Tags } from "lucide-react";
import { toast } from "sonner";
import { FileDropzone } from "@/components/FileDropzone";
import { MARKETPLACES } from "@/lib/marketplaces";
import { converterZplParaPdf, zplDownloadUrl, type ZplConvertResponse } from "@/lib/api";

export const Route = createFileRoute("/zpl-converter")({
  head: () => ({
    meta: [
      { title: "Conversor ZPL para PDF - Conciliador" },
      { name: "description", content: "Conversao local de arquivos ZPL/TXT em PDF multipagina." },
    ],
  }),
  component: ZplConverterPage,
});

function ZplConverterPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [marketplace, setMarketplace] = useState("");
  const [batchName, setBatchName] = useState("");
  const [widthMm, setWidthMm] = useState(100);
  const [heightMm, setHeightMm] = useState(150);
  const [dpi, setDpi] = useState(203);
  const [zplText, setZplText] = useState("");
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<ZplConvertResponse | null>(null);

  const selectedFile = files[0];
  const pastedZpl = zplText.trim();
  const statusLabel = useMemo(() => {
    if (!resultado) return "";
    if (resultado.status === "partial_success") return "Convertido com avisos";
    if (resultado.status === "success") return "Convertido";
    return "Falhou";
  }, [resultado]);

  const onConvert = async () => {
    if (!selectedFile && !pastedZpl) {
      toast.error("Selecione um arquivo ou cole o codigo ZPL");
      return;
    }
    setLoading(true);
    setResultado(null);
    try {
      const source = selectedFile ?? new File([pastedZpl], "codigo_colado.zpl", { type: "text/plain" });
      const data = await converterZplParaPdf(source, {
        marketplace,
        batchName: batchName || undefined,
        widthMm,
        heightMm,
        dpi,
      });
      setResultado(data);
      toast.success("PDF gerado", {
        description: `${data.converted_labels} de ${data.total_labels} etiqueta(s) convertida(s)`,
      });
    } catch (e: any) {
      toast.error("Erro ao converter", { description: e?.message ?? "Tente novamente." });
    } finally {
      setLoading(false);
    }
  };

  const resetConversion = () => {
    setFiles([]);
    setZplText("");
    setBatchName("");
    setResultado(null);
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 p-6 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Conversor ZPL para PDF</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Gera PDF multipagina local a partir de arquivos ZPL ou TXT.
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-4">
          <FileDropzone
            title="Arquivo ZPL/TXT"
            description="Envie um arquivo contendo uma ou varias etiquetas entre ^XA e ^XZ."
            accept=".zpl,.txt"
            acceptedTypes={["ZPL", "TXT"]}
            files={files}
            onFilesChange={(next) => setFiles(next.slice(-1))}
          />

          <section className="rounded-xl border bg-card p-5">
            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Clipboard className="h-4 w-4" />
                Ou cole o codigo ZPL aqui
              </span>
              <textarea
                value={zplText}
                onChange={(e) => setZplText(e.target.value)}
                placeholder="^XA^FO50,50^FDExemplo ZPL^FS^XZ"
                className="min-h-36 w-full resize-y rounded-md border border-input bg-background px-3 py-2.5 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </label>
            <p className="mt-2 text-xs text-muted-foreground">
              Se um arquivo estiver selecionado, ele sera usado. Para converter o texto colado, remova o arquivo da lista.
            </p>
          </section>
        </div>

        <section className="rounded-xl border bg-card p-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Marketplace
              </span>
              <select
                value={marketplace}
                onChange={(e) => setMarketplace(e.target.value)}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="">Nao informado</option>
                {MARKETPLACES.map((m) => (
                  <option key={m.slug} value={m.name}>{m.name}</option>
                ))}
              </select>
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Nome do lote
              </span>
              <input
                value={batchName}
                onChange={(e) => setBatchName(e.target.value)}
                placeholder="Ex.: etiquetas tarde"
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Largura mm
              </span>
              <input
                type="number"
                min={1}
                value={widthMm}
                onChange={(e) => setWidthMm(Number(e.target.value))}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Altura mm
              </span>
              <input
                type="number"
                min={1}
                value={heightMm}
                onChange={(e) => setHeightMm(Number(e.target.value))}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                DPI
              </span>
              <select
                value={dpi}
                onChange={(e) => setDpi(Number(e.target.value))}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value={203}>203</option>
                <option value={300}>300</option>
              </select>
            </label>
            <button
              type="button"
              onClick={onConvert}
              disabled={loading || (!selectedFile && !pastedZpl)}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {loading ? "Convertendo..." : "Converter"}
            </button>
            <button
              type="button"
              onClick={resetConversion}
              disabled={loading}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-input bg-background px-4 text-sm font-medium hover:bg-muted disabled:opacity-60"
            >
              <RotateCcw className="h-4 w-4" />
              Limpar
            </button>
          </div>
        </section>
      </div>

      {loading && (
        <section className="rounded-xl border bg-card p-8 text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
          <p className="mt-3 text-sm font-medium">Processando etiquetas ZPL</p>
          <p className="text-xs text-muted-foreground">Lotes grandes podem levar alguns segundos.</p>
        </section>
      )}

      {resultado && (
        <section className="rounded-xl border bg-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-md bg-success/10 text-success">
                <Tags className="h-5 w-5" />
              </span>
              <div>
                <h2 className="text-base font-semibold">{statusLabel}</h2>
                <p className="text-sm text-muted-foreground">
                  Job {resultado.job_id}
                </p>
              </div>
            </div>
            {resultado.pdf_url && (
              <a
                href={zplDownloadUrl(resultado.job_id)}
                className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                <Download className="h-4 w-4" />
                Baixar PDF
              </a>
            )}
            <button
              type="button"
              onClick={resetConversion}
              className="inline-flex h-10 items-center gap-2 rounded-md border border-input bg-background px-4 text-sm font-medium hover:bg-muted"
            >
              <RotateCcw className="h-4 w-4" />
              Nova conversão
            </button>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border bg-background p-4">
              <p className="text-xs text-muted-foreground">Detectadas</p>
              <p className="mt-1 text-2xl font-semibold">{resultado.total_labels}</p>
            </div>
            <div className="rounded-lg border bg-background p-4">
              <p className="text-xs text-muted-foreground">Convertidas</p>
              <p className="mt-1 text-2xl font-semibold text-success">{resultado.converted_labels}</p>
            </div>
            <div className="rounded-lg border bg-background p-4">
              <p className="text-xs text-muted-foreground">Com erro</p>
              <p className="mt-1 text-2xl font-semibold text-warning">{resultado.failed_labels}</p>
            </div>
          </div>

          {resultado.warnings.length > 0 && (
            <div className="mt-5 rounded-lg border bg-background p-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                <FileText className="h-4 w-4" />
                Avisos
              </div>
              <ul className="space-y-1 text-sm text-muted-foreground">
                {resultado.warnings.slice(0, 8).map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
