"use client";

import { FileText, Building2, ArrowLeft, Sparkles, AlertTriangle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import kpiSources from "@/data/kpi-sources.json";
import { DONNEES_EXTRAITES, estNouvelleSociete, societesTriees } from "@/lib/donnees-extraites-utils";
import { PDF_PAR_SOCIETE } from "@/lib/pdf-par-societe";

/**
 * Onglet Documents — visualiseur PDF, une société = une ligne dans la
 * sidebar, un clic ouvre le PDF de cette société dans un lecteur intégré
 * (iframe pointant vers /api/pdf/<fichier>). Fini l'arborescence
 * dépliable A/B/C/D/E vide : on va directement au document.
 *
 * Arrivée depuis Base de données avec ?company=X&kpi=Y : le PDF de X est
 * ouvert et on saute directement à la page source du KPI (#page=N, géré
 * nativement par le viewer PDF du navigateur).
 *
 * En production, les PDF sont servis depuis Vercel Blob (stockage en ligne).
 * En développement, ils sont lus depuis le dossier data/ local.
 */

type KpiSource = {
  value: number;
  unit: string;
  year: number;
  source_page: number | null;
  source_chapter: string | null;
};
type KpiSources = Record<string, Record<string, KpiSource>>;
const typedKpiSources = kpiSources as KpiSources;

const KPI_LABELS: Record<string, string> = {
  ratio_scr: "Ratio SCR",
  ratio_mcr: "Ratio MCR",
  fonds_propres_eligibles: "Fonds propres éligibles",
  best_estimate: "Best Estimate",
  scr_total: "SCR total",
  mcr: "MCR",
};

/** Résout la page source d'un KPI : essaie kpi-sources.json (Groupama)
 * puis retombe sur donnees-extraites.json (les 34 sociétés). */
function pageSourceKpi(company: string, kpi: string): number | null {
  const via1 = typedKpiSources[company]?.[kpi]?.source_page ?? null;
  if (via1) return via1;
  return DONNEES_EXTRAITES.kpisParSociete[company]?.[kpi]?.pageSource ?? null;
}

export default function DocumentsPage() {
  const societes = useMemo(() => societesTriees(), []);
  const [societeSelectionnee, setSocieteSelectionnee] = useState<string | null>(null);
  const [pageCible, setPageCible] = useState<number | null>(null);
  const [kpiCible, setKpiCible] = useState<string | null>(null);
  const [recherche, setRecherche] = useState("");

  // Arrivée avec ?company=X[&kpi=Y] : on ouvre directement le PDF de X
  // à la bonne page si un KPI est ciblé.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const company = params.get("company");
    const kpi = params.get("kpi");
    if (!company) return;
    setSocieteSelectionnee(company);
    if (kpi) {
      setKpiCible(kpi);
      setPageCible(pageSourceKpi(company, kpi));
    }
  }, []);

  const societesFiltrees = useMemo(() => {
    const q = recherche.trim().toLowerCase();
    if (!q) return societes;
    return societes.filter((s) => s.name.toLowerCase().includes(q));
  }, [societes, recherche]);

  const pdfSociete = societeSelectionnee ? PDF_PAR_SOCIETE[societeSelectionnee] : null;
  const urlPdf = pdfSociete
    ? `/api/pdf/${encodeURIComponent(pdfSociete)}${pageCible ? `#page=${pageCible}` : ""}`
    : null;

  const selectionner = (nom: string) => {
    setSocieteSelectionnee(nom);
    // Nouvelle société sélectionnée = on remet à zéro le KPI ciblé,
    // sinon la page cible resterait "collée" d'une visite précédente.
    setPageCible(null);
    setKpiCible(null);
  };

  return (
    <div className="absolute inset-0 flex overflow-hidden">
      {/* Sidebar : liste plate des sociétés */}
      <div
        className={cn(
          "w-full md:w-80 md:flex-shrink-0 border-r border-border bg-surface overflow-auto",
          societeSelectionnee ? "hidden md:block" : "block"
        )}
      >
        <div className="px-4 py-4 border-b border-border">
          <h3 className="font-heading text-lg text-text-primary">Documents</h3>
          <p className="text-xs text-text-tertiary mt-0.5">
            {societes.length} rapports SFCR — cliquez pour ouvrir
          </p>
          <input
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
            placeholder="Rechercher une société..."
            className="mt-3 w-full text-sm border border-border rounded-[var(--radius-md)] px-3 py-1.5 bg-surface text-text-primary"
          />
        </div>
        <div className="py-2">
          {societesFiltrees.length === 0 && (
            <p className="text-xs text-text-tertiary px-4 py-3">Aucune société ne correspond.</p>
          )}
          {societesFiltrees.map((s) => {
            const actif = societeSelectionnee === s.name;
            const nouvelle = estNouvelleSociete(s.name);
            const aUnPdf = !!PDF_PAR_SOCIETE[s.name];
            return (
              <button
                key={s.id}
                onClick={() => selectionner(s.name)}
                className={cn(
                  "w-full flex items-center gap-2 px-4 py-2.5 text-sm text-left transition-colors",
                  actif
                    ? "bg-accent-light text-accent font-medium"
                    : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                )}
              >
                <Building2 className={cn("w-4 h-4 flex-shrink-0", actif ? "text-accent" : "text-text-tertiary")} />
                <span className="flex-1 truncate">{s.name}</span>
                {nouvelle && (
                  <span
                    title="Société ajoutée à chaud — extraction automatique, à vérifier."
                    className="text-[9px] font-medium uppercase tracking-wide text-warning bg-warning-light px-1.5 py-0.5 rounded flex-shrink-0"
                  >
                    Nouveau
                  </span>
                )}
                {!aUnPdf && (
                  <span
                    title="Aucun PDF associé pour cette société."
                    className="text-[9px] font-medium uppercase tracking-wide text-text-tertiary bg-surface-secondary px-1.5 py-0.5 rounded flex-shrink-0"
                  >
                    Sans PDF
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Zone principale : viewer PDF */}
      <div className={cn("flex-1 flex flex-col min-h-0", societeSelectionnee ? "block" : "hidden md:flex")}>
        {societeSelectionnee ? (
          <>
            <div className="border-b border-border bg-surface px-4 py-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <button
                  onClick={() => setSocieteSelectionnee(null)}
                  className="md:hidden inline-flex items-center gap-1 text-sm text-accent hover:underline flex-shrink-0"
                >
                  <ArrowLeft className="w-4 h-4" />
                </button>
                <FileText className="w-4 h-4 text-accent flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">{societeSelectionnee}</p>
                  {kpiCible && pageCible && (
                    <p className="text-[11px] text-text-tertiary truncate">
                      {KPI_LABELS[kpiCible] ?? kpiCible} — page {pageCible}
                    </p>
                  )}
                </div>
              </div>
              {estNouvelleSociete(societeSelectionnee) && (
                <span className="inline-flex items-center gap-1 text-[10px] font-medium text-warning bg-warning-light px-2 py-0.5 rounded flex-shrink-0">
                  <Sparkles className="w-3 h-3" /> Nouveau — à vérifier
                </span>
              )}
            </div>

            {urlPdf ? (
              // iframe : le lecteur PDF natif du navigateur gère #page=N,
              // le zoom, la recherche. Rien à installer côté frontend.
              // key : force le remount quand la société OU la page change,
              // pour que le #page=N soit bien pris en compte (les navigateurs
              // n'appliquent pas toujours un changement de fragment sur une
              // iframe déjà chargée).
              <iframe
                key={urlPdf}
                src={urlPdf}
                title={`PDF SFCR de ${societeSelectionnee}`}
                className="flex-1 w-full min-h-0 border-0 bg-surface-secondary"
              />
            ) : (
              <PdfIndisponible societe={societeSelectionnee} />
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center px-6">
            <div className="w-14 h-14 rounded-2xl bg-surface-secondary flex items-center justify-center mb-4">
              <FileText className="w-7 h-7 text-text-tertiary" />
            </div>
            <h3 className="font-heading text-xl text-text-primary mb-2">Sélectionnez un document</h3>
            <p className="text-sm text-text-secondary max-w-sm">
              Choisissez une société dans la liste pour ouvrir son rapport SFCR.
            </p>

          </div>
        )}
      </div>
    </div>
  );
}

/** Écran affiché quand la société n'a pas de PDF associé (nouvelle
 * société ajoutée à chaud dont le fichier n'a pas encore de mapping,
 * ou fichier manquant sur disque). */
function PdfIndisponible({ societe }: { societe: string }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
      <div className="w-14 h-14 rounded-2xl bg-warning-light flex items-center justify-center mb-4">
        <AlertTriangle className="w-7 h-7 text-warning" />
      </div>
      <h3 className="font-heading text-xl text-text-primary mb-2">PDF indisponible</h3>
      <p className="text-sm text-text-secondary max-w-md">
        Aucun fichier PDF n&apos;est associé à <strong>{societe}</strong> dans le mapping actuel.
      </p>
      <p className="text-xs text-text-tertiary max-w-md mt-3">
        Si cette société vient d&apos;être ajoutée via l&apos;onglet Upload, le PDF est bien dans data/ mais le mapping
        automatique (nom société → nom de fichier) n&apos;a pas encore été mis à jour. À corriger dans
        src/lib/pdf-par-societe.ts.
      </p>
    </div>
  );
}
