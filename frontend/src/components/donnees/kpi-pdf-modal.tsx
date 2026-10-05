"use client";

import { useEffect, useCallback, useState } from "react";
import { X, ExternalLink, ShieldCheck, Sparkles, Pencil, Send, Loader2, Calculator, ArrowRight } from "lucide-react";
import { formatValeurBrute, formatValeurReelle, type KpiExtrait, type Composant } from "@/lib/donnees-extraites-utils";
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

/** Formate un nombre avec espaces (séparateur de milliers) et virgule décimale */
function fmtComposant(valeur: number, unite: string): string {
  return formatValeurReelle(valeur, unite);
}

/**
 * Modal plein écran affichant le PDF source à la page du KPI sélectionné.
 * Le bouton "Corriger" envoie via le callback onCorrection (hook parent).
 */
export function KpiPdfModal({ kpiId, label, kpi, societe, onClose, onCorrection }: Props) {
  const nomPdf = PDF_PAR_SOCIETE[societe];
  const pdfUrl = nomPdf ? `/api/pdf/${encodeURIComponent(nomPdf)}` : null;

  // --- Navigation page PDF ---
  // viewingPage contrôle quelle page le PDF viewer affiche.
  // viewKey force un remount du PdfPageViewer pour changer de page.
  const [viewingPage, setViewingPage] = useState(kpi.pageSource ?? 1);
  const [viewKey, setViewKey] = useState(0);

  function naviguerVersPage(page: number) {
    setViewingPage(page);
    setViewKey((k) => k + 1);
  }

  // --- Décomposition ---
  const [showDecomposition, setShowDecomposition] = useState(true);
  const hasComposants = kpi.estCompose && kpi.composants && kpi.composants.length > 0;

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
                {hasComposants && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium flex-shrink-0 text-amber-700 bg-amber-100">
                    <Calculator className="w-3 h-3" />
                    Valeur calculée
                  </span>
                )}
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

        {/* Section décomposition — KPIs composés */}
        {hasComposants && (
          <div className="border-b border-border bg-amber-50/30 flex-shrink-0">
            <button
              onClick={() => setShowDecomposition(!showDecomposition)}
              className="w-full flex items-center gap-2 px-4 sm:px-5 py-2 text-left hover:bg-amber-50/50 transition-colors"
            >
              <Calculator className="w-4 h-4 text-amber-600 flex-shrink-0" />
              <span className="text-sm font-medium text-amber-800">Décomposition</span>
              <span className="text-xs text-amber-600">
                ({kpi.composants!.length} composant{kpi.composants!.length > 1 ? "s" : ""})
              </span>
              <svg
                className={`w-4 h-4 text-amber-500 ml-auto transition-transform ${showDecomposition ? "rotate-180" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showDecomposition && (
              <div className="px-4 sm:px-5 pb-3 space-y-1.5">
                {kpi.composants!.map((comp, i) => (
                  <div key={i}>
                    {/* Opérateur entre les composants (sauf avant le premier) */}
                    {i > 0 && (
                      <div className="flex items-center gap-2 py-0.5 pl-2">
                        <span className="text-xs font-mono font-bold text-amber-500">
                          {comp.operation === "-" ? "−" : "+"}
                        </span>
                      </div>
                    )}
                    <button
                      onClick={() => comp.pageSource && naviguerVersPage(comp.pageSource)}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-lg bg-white/70 border border-amber-200/60 hover:border-amber-300 hover:bg-white transition-colors group text-left"
                    >
                      {/* Code QRT */}
                      <span className="font-mono text-xs text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded flex-shrink-0">
                        {comp.codeQrt}
                      </span>
                      {/* Label + valeur */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-text-primary truncate">{comp.label}</p>
                        <p className="text-xs text-text-tertiary">
                          <span className="font-mono font-medium text-text-secondary">{fmtComposant(comp.valeur, comp.unite)}</span>
                          {comp.pageSource != null && " · "}
                          {comp.pageSource != null && (
                            <span className="text-accent group-hover:underline">
                              p.&nbsp;{comp.pageSource}
                            </span>
                          )}
                        </p>
                      </div>
                      {/* Flèche */}
                      <ArrowRight className="w-3.5 h-3.5 text-text-tertiary group-hover:text-accent transition-colors flex-shrink-0" />
                    </button>
                  </div>
                ))}

                {/* Ligne de total */}
                <div className="flex items-center gap-3 px-3 pt-2 mt-1 border-t border-amber-200/60">
                  <span className="text-xs font-medium text-amber-700">Total</span>
                  <span className="font-mono text-sm font-bold text-text-primary">
                    {fmtComposant(
                      kpi.composants!.reduce((acc, c) => acc + (c.operation === "-" ? -c.valeur : c.valeur), 0),
                      kpi.unite
                    )}
                  </span>
                  <span className="text-xs text-text-tertiary ml-auto">
                    Valeur stockée : {formatValeurReelle(kpi.valeur, kpi.unite)}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* PDF viewer */}
        <div className="flex-1 min-h-0">
          {pdfUrl ? (
            <PdfPageViewer
              key={viewKey}
              url={pdfUrl}
              initialPage={viewingPage}
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
