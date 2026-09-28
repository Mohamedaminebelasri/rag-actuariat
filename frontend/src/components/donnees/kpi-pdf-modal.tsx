"use client";

import { useEffect, useCallback } from "react";
import { X, ExternalLink, ShieldCheck, Sparkles } from "lucide-react";
import { formatValeurReelle, type KpiExtrait } from "@/lib/donnees-extraites-utils";
import { PDF_PAR_SOCIETE } from "@/lib/pdf-par-societe";
import { PdfPageViewer } from "./pdf-page-viewer";

type Props = {
  kpiId: string;
  label: string;
  kpi: KpiExtrait;
  societe: string;
  onClose: () => void;
};

/**
 * Modal plein écran (légèrement réduit) affichant le PDF source à la page
 * du KPI sélectionné via un viewer PDF.js. Fonctionne sur tous les
 * navigateurs y compris mobile Safari (pas de #page=N dans iframe).
 */
export function KpiPdfModal({ kpiId, label, kpi, societe, onClose }: Props) {
  const nomPdf = PDF_PAR_SOCIETE[societe];
  // URL sans fragment — la navigation par page est gérée par PdfPageViewer
  const pdfUrl = nomPdf
    ? `/api/pdf/${encodeURIComponent(nomPdf)}`
    : null;

  // Fermer avec Escape
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [handleKeyDown]);

  const source =
    kpi.chapitreSource && kpi.pageSource
      ? `${kpi.chapitreSource}, p. ${kpi.pageSource}`
      : kpi.chapitreSource ?? (kpi.pageSource ? `p. ${kpi.pageSource}` : null);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-3 sm:p-6"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full h-full max-w-[1200px] max-h-[92vh] bg-surface rounded-2xl shadow-2xl border border-border flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between gap-3 px-4 sm:px-5 py-3 border-b border-border bg-surface-secondary/50 flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-heading text-lg text-text-primary truncate">{label}</h3>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium flex-shrink-0 ${
                    kpi.valide
                      ? "text-success bg-success-light"
                      : "text-warning bg-warning-light"
                  }`}
                >
                  {kpi.valide ? (
                    <ShieldCheck className="w-3 h-3" />
                  ) : (
                    <Sparkles className="w-3 h-3" />
                  )}
                  {kpi.valide ? "Vérifié" : "À vérifier"}
                </span>
              </div>
              <p className="text-xs text-text-tertiary mt-0.5 truncate">
                {societe}
                {source ? ` · Source : ${source}` : ""}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            {/* Valeur extraite mise en évidence */}
            <div className="hidden sm:flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-1.5">
              <span className="text-xs text-text-tertiary">Valeur extraite :</span>
              <span className="font-mono text-base font-bold text-text-primary">
                {formatValeurReelle(kpi.valeur, kpi.unite)}
              </span>
            </div>

            {/* Ouvrir dans Documents */}
            {pdfUrl && (
              <a
                href={`/documents?company=${encodeURIComponent(societe)}&kpi=${encodeURIComponent(kpiId)}`}
                className="hidden sm:inline-flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors"
                title="Ouvrir dans l'onglet Documents"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}

            {/* Bouton fermer */}
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
              title="Fermer (Échap)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Valeur sur mobile */}
        <div className="sm:hidden flex items-center gap-2 px-4 py-2 border-b border-border bg-surface">
          <span className="text-xs text-text-tertiary">Valeur extraite :</span>
          <span className="font-mono text-base font-bold text-text-primary">
            {formatValeurReelle(kpi.valeur, kpi.unite)}
          </span>
        </div>

        {/* PDF viewer (pdfjs-dist) */}
        <div className="flex-1 min-h-0">
          {pdfUrl ? (
            <PdfPageViewer
              url={pdfUrl}
              initialPage={kpi.pageSource ?? 1}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-text-tertiary">
              <p className="text-sm">
                Aucun PDF associé à {societe} pour le moment.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
