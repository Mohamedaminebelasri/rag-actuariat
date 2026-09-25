"use client";

import { BarChart3, TrendingUp, TrendingDown, Minus, Download } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

// Placeholder KPI data — les valeurs affichées restent des exemples
// (le dashboard n'est pas encore branché sur kpis.db), mais chaque
// carte porte le vrai kpi_name pour permettre le lien intelligent vers
// l'annexe QRT source (Documents utilise ce kpi_name + l'entreprise
// pour retrouver la vraie source_page dans kpis.db).
const kpis = [
  {
    label: "Ratio SCR",
    kpiName: "ratio_scr",
    value: "267%",
    change: "+12 pts",
    trend: "up" as const,
    description: "Capital de solvabilité requis",
  },
  {
    label: "Ratio MCR",
    kpiName: "ratio_mcr",
    value: "589%",
    change: "+8 pts",
    trend: "up" as const,
    description: "Minimum de capital requis",
  },
  {
    label: "Fonds propres",
    kpiName: "fonds_propres_eligibles",
    value: "14.2 Md€",
    change: "-0.3 Md€",
    trend: "down" as const,
    description: "Fonds propres éligibles",
  },
  {
    label: "Best Estimate",
    kpiName: "best_estimate",
    value: "52.8 Md€",
    change: "−0.1%",
    trend: "neutral" as const,
    description: "Provisions techniques",
  },
];

const ENTREPRISE_ACTIVE = "Groupama";

const TrendIcon = ({ trend }: { trend: "up" | "down" | "neutral" }) => {
  if (trend === "up") return <TrendingUp className="w-3.5 h-3.5 text-success" />;
  if (trend === "down") return <TrendingDown className="w-3.5 h-3.5 text-danger" />;
  return <Minus className="w-3.5 h-3.5 text-text-tertiary" />;
};

// Placeholder table data
const comparatif = [
  { nom: "Groupama", scr: "267%", mcr: "589%", fp: "14.2 Md€", statut: "Conforme" },
  { nom: "Assureur B", scr: "—", mcr: "—", fp: "—", statut: "Non chargé" },
  { nom: "Assureur C", scr: "—", mcr: "—", fp: "—", statut: "Non chargé" },
];

export default function AnalysePage() {
  const router = useRouter();

  const goToQrtSource = (kpiName: string) => {
    router.push(
      `/documents?company=${encodeURIComponent(ENTREPRISE_ACTIVE)}&kpi=${encodeURIComponent(kpiName)}`
    );
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="font-heading text-2xl text-text-primary">Analyse</h2>
            <p className="text-sm text-text-secondary mt-1">
              KPIs et comparaison des ratios de solvabilité
            </p>
          </div>
          <button className="inline-flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] border border-border text-sm text-text-secondary hover:bg-surface-hover transition-colors">
            <Download className="w-4 h-4" />
            Exporter
          </button>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {kpis.map((kpi) => (
            <button
              key={kpi.label}
              onClick={() => goToQrtSource(kpi.kpiName)}
              title="Voir la source dans les Annexes QRT"
              className="text-left bg-surface border border-border rounded-[var(--radius-lg)] p-5 hover:shadow-[var(--shadow-md)] hover:border-accent/40 transition-all cursor-pointer"
            >
              <p className="text-xs text-text-tertiary uppercase tracking-wider mb-1">
                {kpi.label}
              </p>
              <p className="font-mono text-2xl font-semibold text-text-primary mb-1">
                {kpi.value}
              </p>
              <div className="flex items-center gap-1.5">
                <TrendIcon trend={kpi.trend} />
                <span
                  className={cn(
                    "text-xs font-medium",
                    kpi.trend === "up" && "text-success",
                    kpi.trend === "down" && "text-danger",
                    kpi.trend === "neutral" && "text-text-tertiary"
                  )}
                >
                  {kpi.change}
                </span>
              </div>
              <p className="text-[10px] text-text-tertiary mt-2">
                {kpi.description}
              </p>
            </button>
          ))}
        </div>

        {/* Comparatif Table */}
        <div className="bg-surface border border-border rounded-[var(--radius-lg)] overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="font-heading text-lg text-text-primary">
              Tableau comparatif
            </h3>
            <p className="text-xs text-text-tertiary mt-0.5">
              Comparaison multi-assureurs des ratios clés
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-secondary">
                  <th className="text-left px-5 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                    Organisme
                  </th>
                  <th className="text-right px-5 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                    Ratio SCR
                  </th>
                  <th className="text-right px-5 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                    Ratio MCR
                  </th>
                  <th className="text-right px-5 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                    Fonds propres
                  </th>
                  <th className="text-center px-5 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                    Statut
                  </th>
                </tr>
              </thead>
              <tbody>
                {comparatif.map((row, i) => (
                  <tr
                    key={row.nom}
                    className={cn(
                      "border-b border-border last:border-0 hover:bg-surface-hover transition-colors",
                      i === 0 && "bg-accent-light/30"
                    )}
                  >
                    <td className="px-5 py-3.5 font-medium text-text-primary">
                      {row.nom}
                    </td>
                    <td className="px-5 py-3.5 text-right font-mono text-text-primary">
                      {row.scr}
                    </td>
                    <td className="px-5 py-3.5 text-right font-mono text-text-primary">
                      {row.mcr}
                    </td>
                    <td className="px-5 py-3.5 text-right font-mono text-text-primary">
                      {row.fp}
                    </td>
                    <td className="px-5 py-3.5 text-center">
                      <span
                        className={cn(
                          "inline-flex px-2.5 py-1 rounded-full text-xs font-medium",
                          row.statut === "Conforme"
                            ? "bg-success-light text-success"
                            : "bg-surface-secondary text-text-tertiary"
                        )}
                      >
                        {row.statut}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
