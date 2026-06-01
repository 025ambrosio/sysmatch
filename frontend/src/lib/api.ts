// API service layer — fala com FastAPI local quando configurado, senão usa mocks.

import { historicoMock, resumoMock, conciliadosMock, etiquetasSemNfMock, nfsSemEtiquetaMock, revisarMock } from "./mocks";
import { MARKETPLACES } from "./marketplaces";

const URL_KEY = "conciliador_api_url";
const ZPL_URL_KEY = "conciliador_zpl_api_url";
const DEFAULT_API_URL = "http://localhost:8010";

export function getApiUrl(): string {
  if (typeof window === "undefined") return DEFAULT_API_URL;
  const savedUrl = localStorage.getItem(URL_KEY)?.trim();
  if (!savedUrl || savedUrl === "http://localhost:8000" || savedUrl === "http://localhost:8501") {
    return DEFAULT_API_URL;
  }
  return savedUrl;
}
export function setApiUrl(url: string) {
  localStorage.setItem(URL_KEY, url.trim());
}

export function getZplApiUrl(): string {
  if (typeof window === "undefined") return DEFAULT_API_URL;
  const savedUrl = localStorage.getItem(ZPL_URL_KEY)?.trim();
  return savedUrl || getApiUrl();
}

export function setZplApiUrl(url: string) {
  localStorage.setItem(ZPL_URL_KEY, url.trim());
}

export interface LoteTotals {
  notas_lidas: number;
  etiquetas_lidas: number;
  conciliadas: number;
  etiquetas_sem_nf: number;
  notas_sem_etiqueta: number;
  para_revisar: number;
  taxa_conciliacao: number;
}

export interface LoteViews {
  conciliados: any[];
  etiquetas_sem_nf: any[];
  notas_sem_etiqueta: any[];
  revisar: any[];
}

export interface LoteResponse {
  job_id: string;
  marketplace: string;
  marketplace_slug: string;
  batch_name?: string;
  created_at?: string;
  status?: string;
  totals: LoteTotals;
  views?: LoteViews;
  downloads?: Record<string, string | boolean>;
  errors?: Record<string, string[]>;
}

export interface OpcoesProcessamento {
  marketplace: string;
  batchName?: string;
}

export interface ZplConvertOptions {
  marketplace?: string;
  batchName?: string;
  widthMm: number;
  heightMm: number;
  dpi: number;
}

export interface ZplConvertResponse {
  job_id: string;
  status: "success" | "partial_success" | "failed";
  total_labels: number;
  converted_labels: number;
  failed_labels: number;
  pdf_url?: string | null;
  warnings: string[];
}

const LOCAL_JOBS_KEY = "conciliador_local_jobs";

function readLocalJobs(): LoteResponse[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(LOCAL_JOBS_KEY) ?? "[]");
  } catch {
    return [];
  }
}
function writeLocalJobs(jobs: LoteResponse[]) {
  localStorage.setItem(LOCAL_JOBS_KEY, JSON.stringify(jobs.slice(0, 100)));
}

function nowJobId() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const ts = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  return `${ts}_${Math.random().toString(36).slice(2, 10)}`;
}

export async function processarLote(
  nfeFiles: File[],
  labelFiles: File[],
  opts: OpcoesProcessamento,
): Promise<LoteResponse> {
  const base = getApiUrl();
  const fd = new FormData();
  nfeFiles.forEach((f) => fd.append("nfe_files", f));
  labelFiles.forEach((f) => fd.append("label_files", f));
  fd.append("marketplace", opts.marketplace);
  if (opts.batchName) fd.append("batch_name", opts.batchName);
  fd.append("print_layout", "picking");
  fd.append("paper_size", "4x6");
  fd.append("picking_format", "lines");
  fd.append("thermal_mode", "true");
  fd.append("thermal_intensity", "strong");
  fd.append("remove_white_margins", "true");
  fd.append("print_order", "label_first");
  fd.append("sort_by", "label_order");
  fd.append("nfe_layout", "full_page");

  if (base) {
    const res = await fetch(`${base}/api/processar-lote`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(`Erro ${res.status} ao processar lote`);
    const data: LoteResponse = await res.json();
    return data;
  }

  // === Modo demo ===
  await new Promise((r) => setTimeout(r, 900));
  const slug = MARKETPLACES.find((m) => m.name === opts.marketplace)?.slug ?? "shopee";
  const job: LoteResponse = {
    job_id: nowJobId(),
    marketplace: opts.marketplace,
    marketplace_slug: slug,
    batch_name: opts.batchName || `Lote ${new Date().toLocaleString("pt-BR")}`,
    created_at: new Date().toISOString(),
    totals: {
      notas_lidas: resumoMock.nfsLidas,
      etiquetas_lidas: resumoMock.etiquetasLidas,
      conciliadas: resumoMock.conciliadas,
      etiquetas_sem_nf: resumoMock.etiquetasSemNf,
      notas_sem_etiqueta: resumoMock.nfsSemEtiqueta,
      para_revisar: resumoMock.paraRevisar,
      taxa_conciliacao: resumoMock.taxaConciliacao,
    },
    views: {
      conciliados: conciliadosMock,
      etiquetas_sem_nf: etiquetasSemNfMock,
      notas_sem_etiqueta: nfsSemEtiquetaMock,
      revisar: revisarMock,
    },
  };
  const jobs = readLocalJobs();
  writeLocalJobs([job, ...jobs]);
  return job;
}

export async function listarLotes(marketplace?: string): Promise<LoteResponse[]> {
  const base = getApiUrl();
  if (base) {
    const url = new URL(`${base}/api/lotes`);
    if (marketplace) url.searchParams.set("marketplace", marketplace);
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error("Falha ao listar lotes");
    const data = await res.json();
    return Array.isArray(data) ? data : data.lotes ?? [];
  }
  const local = readLocalJobs();
  const seedSlug = "shopee";
  const seed: LoteResponse[] = historicoMock.map((l, i) => ({
    job_id: l.id,
    marketplace: i % 6 === 0 ? "Amazon" : "Shopee",
    marketplace_slug: i % 6 === 0 ? "amazon" : seedSlug,
    batch_name: l.nome,
    created_at: new Date(Date.now() - i * 86400000).toISOString(),
    totals: {
      notas_lidas: l.nfs,
      etiquetas_lidas: l.etiquetas,
      conciliadas: l.conciliadas,
      etiquetas_sem_nf: Math.max(0, l.etiquetas - l.conciliadas),
      notas_sem_etiqueta: Math.max(0, l.nfs - l.conciliadas),
      para_revisar: l.pendentes,
      taxa_conciliacao: Math.round((l.conciliadas / Math.max(1, l.nfs)) * 100),
    },
  }));
  const all = [...local, ...seed];
  return marketplace ? all.filter((j) => j.marketplace === marketplace) : all;
}

export async function getLote(jobId: string): Promise<LoteResponse | null> {
  const base = getApiUrl();
  if (base) {
    const res = await fetch(`${base}/api/lotes/${jobId}`);
    if (!res.ok) return null;
    return res.json();
  }
  const all = await listarLotes();
  return all.find((j) => j.job_id === jobId) ?? null;
}

export function downloadUrls(jobId: string) {
  const base = getApiUrl() || "";
  return {
    pdfFinal: `${base}/api/lotes/${jobId}/arquivos/pdf_final`,
    excel: `${base}/api/lotes/${jobId}/arquivos/relatorio_excel`,
    zipIndividuais: `${base}/api/lotes/${jobId}/arquivos/zip_individuais`,
  };
}

export async function converterZplParaPdf(file: File, opts: ZplConvertOptions): Promise<ZplConvertResponse> {
  const base = getZplApiUrl();
  if (!base) throw new Error("Configure a URL da API antes de converter ZPL.");

  const fd = new FormData();
  fd.append("file", file);
  if (opts.marketplace) fd.append("marketplace", opts.marketplace);
  if (opts.batchName) fd.append("batch_name", opts.batchName);
  fd.append("width_mm", String(opts.widthMm));
  fd.append("height_mm", String(opts.heightMm));
  fd.append("dpi", String(opts.dpi));

  const res = await fetch(`${base}/api/zpl/convert`, { method: "POST", body: fd });
  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    const detail = payload?.detail;
    if (typeof detail === "string") throw new Error(detail);
    if (detail?.message) throw new Error(detail.message);
    throw new Error(`Erro ${res.status} ao converter ZPL`);
  }
  return res.json();
}

export function zplDownloadUrl(jobId: string) {
  return `${getZplApiUrl()}/api/zpl/${jobId}/pdf`;
}

export async function testarConexao(): Promise<{ ok: boolean; mensagem: string }> {
  const url = getApiUrl();
  if (!url) return { ok: false, mensagem: "Nenhuma URL configurada — usando modo demo." };
  try {
    const res = await fetch(`${url}/api/marketplaces`);
    if (res.ok) return { ok: true, mensagem: `Conectado em ${url}` };
    return { ok: false, mensagem: `Backend respondeu ${res.status}` };
  } catch (e) {
    return { ok: false, mensagem: `Não foi possível conectar em ${url}` };
  }
}

export async function testarConexaoZpl(): Promise<{ ok: boolean; mensagem: string }> {
  const url = getZplApiUrl();
  if (!url) return { ok: false, mensagem: "Nenhuma URL configurada para o conversor ZPL." };
  try {
    const res = await fetch(`${url}/openapi.json`);
    if (!res.ok) return { ok: false, mensagem: `API ZPL respondeu ${res.status}` };
    const text = await res.text();
    if (text.includes("/api/zpl/convert")) return { ok: true, mensagem: `Conversor ZPL conectado em ${url}` };
    return { ok: false, mensagem: `API em ${url} nao tem a rota /api/zpl/convert` };
  } catch {
    return { ok: false, mensagem: `Nao foi possivel conectar na API ZPL em ${url}` };
  }
}
