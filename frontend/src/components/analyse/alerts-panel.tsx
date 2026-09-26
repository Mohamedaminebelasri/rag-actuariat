"use client";

import { CircleAlert, CircleCheck, TriangleAlert } from "lucide-react";
import { buildAlertes, type Alerte } from "@/lib/analyse-utils";

const ICONES: Record<Alerte["type"], React.ReactNode> = {
  critique: <CircleAlert className="w-4 h-4 text-danger flex-shrink-0" />,
  conforme: <CircleCheck className="w-4 h-4 text-success flex-shrink-0" />,
  attention: <TriangleAlert className="w-4 h-4 text-warning flex-shrink-0" />,
};

/** Port de section_alertes()/ligne_alerte() (comparative.py, Reflex). */
export function AlertsPanel({ societesComparees }: { societesComparees: string[] }) {
  const alertes = buildAlertes(societesComparees);
  if (alertes.length === 0) return null;

  return (
    <div className="bg-surface border border-border rounded-[var(--radius-lg)] p-5 w-full">
      <p className="font-heading italic text-lg text-text-primary mb-3">Alertes et points d&apos;attention</p>
      <div className="flex flex-col">
        {alertes.map((a, i) => (
          <div key={i} className="flex items-center gap-2.5 py-2.5 border-b border-border last:border-0">
            {ICONES[a.type]}
            <span className="text-sm text-text-primary">{a.texte}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
