import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  tone?: "default" | "success" | "warning" | "destructive" | "info";
}

const toneClass: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  default: "bg-card text-foreground border-border",
  success: "bg-card text-foreground border-border [&_.metric-icon]:bg-success/10 [&_.metric-icon]:text-success",
  warning: "bg-card text-foreground border-border [&_.metric-icon]:bg-warning/15 [&_.metric-icon]:text-warning",
  destructive: "bg-card text-foreground border-border [&_.metric-icon]:bg-destructive/10 [&_.metric-icon]:text-destructive",
  info: "bg-card text-foreground border-border [&_.metric-icon]:bg-info/10 [&_.metric-icon]:text-info",
};

export function MetricCard({ label, value, hint, icon, tone = "default" }: MetricCardProps) {
  return (
    <div className={cn("rounded-xl border p-5 shadow-sm", toneClass[tone])}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
          {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
        </div>
        {icon && (
          <div className="metric-icon flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
