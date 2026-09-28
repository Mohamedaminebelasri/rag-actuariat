"use client";

import { useEffect, useCallback, useState } from "react";
import { X, ExternalLink, ShieldCheck, Sparkles, Pencil, Send, Loader2 } from "lucide-react";
import { formatValeurBrute, type KpiExtrait } from "@/lib/donnees-extraites-utils";
import { PDF_PAR_SOCIETE } from "@/lib/pdf-par-societe";
import { PdfPageViewer } from "./pdf-page-viewer";

/** Dernier zoom utilisé dans le modal KPI (persiste entre ouvertures) */
let lastKpiZoom = 3;

type Props = {
  kpiId: string;
  label: string;
  kpi: KpiExtrait;
  societe: string;
  onClose: () => void;
  /** Callback pour soumettre une correction. Retourne true si succès. */
  onCorrection?: (societe: string, kpiId: string, valeur: string, commentaire: string | null) => Promise<boolean>;
};

/**
 * Modal plein écran affichant le PDF source à la page du KPI sélectionné.
 * Le bouton "Corriger" envoie via le callback onCorrection (hook parent).
 */
export function KpiPdfModal({ kpiId, label, kpi, societe, onClose, onCorrection }: Props) {
  const nomPdf = PDF_PAR_SOCIETE[societe];
  const pdfUrl = nomPdf ? `/api/pdf/${encodeURIComponent(nomPdf)}` : null;

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

  // --- Correction ---
  const [showCorrection, setShowCorrection] = useState(false);
  const [correctionValeur, setCorrectionValeur] = useState("");
  const [correctionCommentaire, setCorrectionCommentaire] = useState("");
  const [correctionEnCours, setCorrectionEnCours] = useState(false);
  const [correctionOk, setCorrectionOk] = useState(false);

  async function envoyerCorrection() {
    if (!correctionValeur.trim()) return;
    setCorrectionEnCours(true);
    try {
      let ok = false;
      if (onCorrection) {
        ok = await onCorrection(
          societe,
          kpiId,
          correctionValeur.trim(),
          correctionCommentaire.trim() || null
        );
      } else {
        // Fallback direct si pas de callback
        const res = await fetch("/api/kpi/correct", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            societe,
            kpiId,
            valeurCorrigee: correctionValeur.trim(),
            commentaire: correctionCommentaire.trim() || null,
          }),
        });
        ok = res.ok;
      }
      if (ok) {
        setCorrectionOk(true);
        setTimeout(() => {
          setShowCorrection(false);
          setCorrectionOk(false);
          setCorrectionValeur("");
          setCorrectionCommentaire("");
        }, 2000);
      }
    } catch {
      // silently fail
    } finally {
      setCorrectionEnCours(false);
    }
  }

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
                {formatValeurBrute(kpi.valeurBrute, kpi.uniteBrute, kpi.valeur, kpi.unite)}
              </span>
              <button
                onClick={() => setShowCorrection(!showCorrection)}
                className="ml-1 w-7 h-7 flex items-center justify-center rounded-md text-text-tertiary hover:text-accent hover:bg-accent/10 transition-colors"
                title="Corriger cette valeur"
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
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
            {formatValeurBrute(kpi.valeurBrute, kpi.uniteBrute, kpi.valeur, kpi.unite)}
          </span>
          <button
            onClick={() => setShowCorrection(!showCorrection)}
            className="ml-1 w-7 h-7 flex items-center justify-center rounded-md text-text-tertiary hover:text-accent hover:bg-accent/10 transition-colors"
            title="Corriger cette valeur"
          >
            <Pencil className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Formulaire de correction */}
        {showCorrection && (
          <div className="px-4 sm:px-5 py-3 border-b border-border bg-amber-50/50 flex-shrink-0">
            {correctionOk ? (
              <p className="text-sm text-success font-medium">Correction enregistrée !</p>
            ) : (
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="flex-1 flex flex-col sm:flex-row gap-2">
                  <div className="flex-shrink-0">
                    <label className="text-[11px] text-text-tertiary block mb-0.5">Valeur corrigée</label>
                    <input
                      type="text"
                      value={correctionValeur}
                      onChange={(e) => setCorrectionValeur(e.target.value)}
                      placeholder="Ex : 54 487 486"
                      className="w-full sm:w-44 px-2.5 py-1.5 text-sm font-mono border border-border rounded-lg bg-surface focus:outline-none focus:ring-2 focus:ring-accent/30"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="text-[11px] text-text-tertiary block mb-0.5">Commentaire (optionnel)</label>
                    <input
                      type="text"
                      value={correctionCommentaire}
                      onChange={(e) => setCorrectionCommentaire(e.target.value)}
                      placeholder="Ex : valeur lue en K€ ligne R0010 colonne C0010"
                      className="w-full px-2.5 py-1.5 text-sm border border-border rounded-lg bg-surface focus:outline-none focus:ring-2 focus:ring-accent/30"
                    />
                  </div>
                </div>
                <button
                  onClick={envoyerCorrection}
                  disabled={!correctionValeur.trim() || correctionEnCours}
                  className="self-end sm:self-end px-3 py-1.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
                >
                  {correctionEnCours ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  Envoyer
                </button>
              </div>
            )}
          </div>
        )}

        {/* PDF viewer */}
        <div className="flex-1 min-h-0">
          {pdfUrl ? (
            <PdfPageViewer
              url={pdfUrl}
              initialPage={kpi.pageSource ?? 1}
              defaultZoom={lastKpiZoom}
              onZoomChange={(z) => { lastKpiZoom = z; }}
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
