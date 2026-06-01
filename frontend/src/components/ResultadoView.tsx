import { FileDown, FileSpreadsheet, Archive } from "lucide-react";
import { MetricCard } from "@/components/MetricCard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { downloadUrls, type LoteResponse } from "@/lib/api";

export function ResultadoView({ lote }: { lote: LoteResponse }) {
  const t = lote.totals;
  const urls = downloadUrls(lote.job_id);
  const hasDownload = (key: string) => {
    const value = lote.downloads?.[key];
    return value === undefined || value === true || Boolean(value);
  };
  const views = lote.views ?? {
    conciliados: [],
    etiquetas_sem_nf: [],
    notas_sem_etiqueta: [],
    revisar: [],
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold">
              {lote.batch_name || "Lote processado"} - {lote.marketplace}
            </h3>
            <p className="text-xs text-muted-foreground">
              ID: <code className="rounded bg-muted px-1.5 py-0.5">{lote.job_id}</code>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {hasDownload("pdf_final") && (
              <DownloadBtn href={urls.pdfFinal} icon={<FileDown className="h-4 w-4" />}>
                Baixar etiqueta consolidada (PDF)
              </DownloadBtn>
            )}
            {hasDownload("relatorio_excel") && (
              <DownloadBtn href={urls.excel} icon={<FileSpreadsheet className="h-4 w-4" />} variant="outline">
                Baixar relatorio Excel
              </DownloadBtn>
            )}
            {hasDownload("zip_individuais") && (
              <DownloadBtn href={urls.zipIndividuais} icon={<Archive className="h-4 w-4" />} variant="outline">
                ZIP individuais
              </DownloadBtn>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <MetricCard label="Notas lidas" value={t.notas_lidas} tone="info" />
        <MetricCard label="Etiquetas lidas" value={t.etiquetas_lidas} tone="info" />
        <MetricCard label="Conciliadas" value={t.conciliadas} tone="success" />
        <MetricCard label="Etiquetas sem NF" value={t.etiquetas_sem_nf} tone="warning" />
        <MetricCard label="NFs sem etiqueta" value={t.notas_sem_etiqueta} tone="destructive" />
        <MetricCard label="Para revisar" value={t.para_revisar} tone="warning" />
      </div>

      <section className="rounded-xl border bg-card">
        <header className="border-b px-5 py-4">
          <h3 className="text-base font-semibold">Verificar pendencias</h3>
          <p className="text-xs text-muted-foreground">
            Detalhamento dos itens conciliados e pendentes deste lote.
          </p>
        </header>
        <div className="p-4">
          <Tabs defaultValue="conciliados" className="space-y-4">
            <TabsList className="flex flex-wrap">
              <TabsTrigger value="conciliados">Conciliados ({views.conciliados.length})</TabsTrigger>
              <TabsTrigger value="sem-nf">Etiquetas sem NF ({views.etiquetas_sem_nf.length})</TabsTrigger>
              <TabsTrigger value="sem-etiqueta">NFs sem etiqueta ({views.notas_sem_etiqueta.length})</TabsTrigger>
              <TabsTrigger value="revisar">Revisar ({views.revisar.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="conciliados">
              <DynTable rows={views.conciliados} empty="Nenhum item conciliado." />
            </TabsContent>
            <TabsContent value="sem-nf">
              <DynTable rows={views.etiquetas_sem_nf} empty="Sem etiquetas pendentes de NF." />
            </TabsContent>
            <TabsContent value="sem-etiqueta">
              <DynTable rows={views.notas_sem_etiqueta} empty="Sem NFs pendentes de etiqueta." />
            </TabsContent>
            <TabsContent value="revisar">
              <DynTable rows={views.revisar} empty="Nada para revisar." />
            </TabsContent>
          </Tabs>
        </div>
      </section>
    </div>
  );
}

function DownloadBtn({
  href,
  icon,
  children,
  variant = "primary",
}: {
  href: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  variant?: "primary" | "outline";
}) {
  const cls =
    variant === "primary"
      ? "bg-primary text-primary-foreground hover:bg-primary/90"
      : "border border-input bg-background hover:bg-muted";
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className={`inline-flex items-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium ${cls}`}
    >
      {icon}
      {children}
    </a>
  );
}

function DynTable({ rows, empty }: { rows: any[]; empty: string }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="rounded-md border border-dashed bg-muted/30 px-4 py-10 text-center text-sm text-muted-foreground">
        {empty}
      </div>
    );
  }
  const cols = Array.from(
    rows.reduce<Set<string>>((acc, r) => {
      Object.keys(r ?? {}).forEach((k) => acc.add(k));
      return acc;
    }, new Set()),
  );
  return (
    <div className="overflow-x-auto rounded-md border">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            {cols.map((c) => (
              <th key={c} className="whitespace-nowrap px-3 py-2">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t hover:bg-muted/30">
              {cols.map((c) => (
                <td key={c} className="whitespace-nowrap px-3 py-2 align-top">
                  {formatCell(r?.[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(v: any) {
  if (v == null) return <span className="text-muted-foreground">-</span>;
  if (typeof v === "object") return <code className="text-xs">{JSON.stringify(v)}</code>;
  return String(v);
}
