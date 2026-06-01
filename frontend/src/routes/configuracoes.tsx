import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Loader2, Plug } from "lucide-react";
import { toast } from "sonner";
import { getApiUrl, setApiUrl, testarConexao } from "@/lib/api";

export const Route = createFileRoute("/configuracoes")({
  head: () => ({
    meta: [
      { title: "Configurações · Conciliador NF-e x Etiquetas" },
      { name: "description", content: "Configurações de impressão, OCR e backend." },
    ],
  }),
  component: Configuracoes,
});

function Configuracoes() {
  const [formato, setFormato] = useState("a4_4");
  const [margem, setMargem] = useState(8);
  const [picking, setPicking] = useState(true);
  const [campoEan, setCampoEan] = useState(true);
  const [campoProduto, setCampoProduto] = useState(true);
  const [campoQtd, setCampoQtd] = useState(true);
  const [modoOcr, setModoOcr] = useState("automatico");
  const [debugOcr, setDebugOcr] = useState(false);
  const [apiUrl, setApiUrlState] = useState("http://192.168.15.2:8010");
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    setApiUrlState(getApiUrl());
  }, []);

  const onTest = async () => {
    setApiUrl(apiUrl);
    setTesting(true);
    const r = await testarConexao();
    setTesting(false);
    if (r.ok) toast.success("Conectado", { description: r.mensagem });
    else toast.error("Sem conexão", { description: r.mensagem });
  };

  const saveAll = () => {
    setApiUrl(apiUrl);
    toast.success("Configurações salvas");
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6 lg:p-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Configurações</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ajuste impressão, OCR e a conexão com o backend FastAPI local.
        </p>
      </div>

      <Section title="Impressão" desc="Layout padrão dos PDFs gerados.">
        <Grid>
          <Field label="Formato padrão">
            <select value={formato} onChange={(e) => setFormato(e.target.value)} className="sel">
              <option value="a4_4">A4 — 4 por folha</option>
              <option value="a4_2">A4 — 2 por folha</option>
              <option value="termica_4x6">4x6 térmica</option>
            </select>
          </Field>
          <Field label="Margem do PDF (mm)">
            <input
              type="number"
              min={0}
              max={30}
              value={margem}
              onChange={(e) => setMargem(Number(e.target.value))}
              className="sel"
            />
          </Field>
          <Toggle label="Mostrar bloco de picking" checked={picking} onChange={setPicking} />
        </Grid>
        <div className="mt-4 rounded-lg border bg-muted/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Campos do picking
          </p>
          <div className="mt-2 flex flex-wrap gap-3">
            <Check label="EAN" checked={campoEan} onChange={setCampoEan} />
            <Check label="Produto" checked={campoProduto} onChange={setCampoProduto} />
            <Check label="Quantidade" checked={campoQtd} onChange={setCampoQtd} />
          </div>
        </div>
      </Section>

      <Section title="OCR" desc="Como o backend deve interpretar etiquetas em imagem.">
        <Grid>
          <Field label="Modo padrão">
            <select value={modoOcr} onChange={(e) => setModoOcr(e.target.value)} className="sel">
              <option value="rapido">Rápido</option>
              <option value="automatico">Automático</option>
              <option value="detalhado">Detalhado</option>
            </select>
          </Field>
          <Toggle label="Mostrar debug OCR nos resultados" checked={debugOcr} onChange={setDebugOcr} />
        </Grid>
      </Section>

      <Section title="Backend" desc="URL da API FastAPI local executando o motor de conciliação.">
        <Grid>
          <Field label="URL da API local">
            <input
              value={apiUrl}
              onChange={(e) => setApiUrlState(e.target.value)}
              placeholder="http://localhost:8000"
              className="sel"
            />
          </Field>
          <div className="flex items-end">
            <button
              onClick={onTest}
              disabled={testing}
              className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-60"
            >
              {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plug className="h-4 w-4" />}
              Testar conexão
            </button>
          </div>
        </Grid>
      </Section>

      <div className="flex justify-end">
        <button
          onClick={saveAll}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Salvar configurações
        </button>
      </div>

      <style>{`
        .sel {
          width: 100%;
          border: 1px solid var(--color-border);
          background: var(--color-background);
          border-radius: 0.5rem;
          padding: 0.55rem 0.75rem;
          font-size: 0.875rem;
        }
        .sel:focus { outline: 2px solid var(--color-ring); outline-offset: 1px; }
      `}</style>
    </div>
  );
}

function Section({ title, desc, children }: { title: string; desc?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border bg-card p-5">
      <header className="mb-4">
        <h2 className="text-base font-semibold">{title}</h2>
        {desc && <p className="text-xs text-muted-foreground">{desc}</p>}
      </header>
      {children}
    </section>
  );
}
function Grid({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-4 md:grid-cols-2">{children}</div>;
}
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}
function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center justify-between rounded-md border bg-background px-3 py-2.5">
      <span className="text-sm">{label}</span>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 rounded-full transition-colors ${checked ? "bg-primary" : "bg-muted-foreground/30"}`}
      >
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${checked ? "translate-x-4" : "translate-x-0.5"}`} />
      </button>
    </label>
  );
}
function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-input accent-[color:var(--color-primary)]"
      />
      {label}
    </label>
  );
}
