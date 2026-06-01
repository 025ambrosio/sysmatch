import type { LoteResponse } from "@/lib/api";

export type LoteStatus = "concluido" | "pendencia" | "erro" | "processando";

export function totalPendencias(lote: LoteResponse): number {
  const totals = lote.totals;
  return totals.etiquetas_sem_nf + totals.notas_sem_etiqueta + totals.para_revisar;
}

export function getLoteStatus(lote: LoteResponse): LoteStatus {
  if (lote.status === "erro") return "erro";
  if (lote.status === "processando") return "processando";
  if (totalPendencias(lote) > 0) return "pendencia";
  if (lote.totals.conciliadas > 0) return "concluido";
  return "erro";
}

export function loteStatusLabel(status: LoteStatus): string {
  return {
    concluido: "Concluído",
    pendencia: "Com pendência",
    erro: "Erro",
    processando: "Em processamento",
  }[status];
}

export function loteStatusClass(status: LoteStatus): string {
  return {
    concluido: "border-success/30 bg-success/10 text-success",
    pendencia: "border-warning/40 bg-warning/15 text-warning-foreground",
    erro: "border-destructive/30 bg-destructive/10 text-destructive",
    processando: "border-info/30 bg-info/10 text-info",
  }[status];
}
