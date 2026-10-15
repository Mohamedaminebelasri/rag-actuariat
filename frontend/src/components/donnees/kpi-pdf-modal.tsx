"use client";

import { useEffect, useCallback, useState } from "react";
import { X, ExternalLink, ShieldCheck, Sparkles, Pencil, Send, Loader2, Calculator, ArrowRight, UserCheck, CheckCircle2, Scale, Info } from "lucide-react";
import {
  DECIMALES_KPIS,
  TOLERANCE_RECALCUL,
  formatValeurBrute,
  formatValeurReelle,
  labelKpi,
  recalculerKpi,
  type KpiExtrait,
  type Composant,
} from "@/lib/donnees-extraites-utils";
import { PDF_PAR_SOCIETE } from "@/lib/pdf-par-societe";
import type { ValidationHumaine } from "@/lib/use-validations-humaines";
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
  /** Validation humaine existante (si déjà traité) */
  validationHumaine?: ValidationHumaine | null;
  /** Callback pour marquer comme traité par un humain */
  onValidation?: (societe: string, kpiId: string, par?: string) => Promise<boolean>;
  /** KPI calculé : ouvre le détail d'un composant qui est lui-même un KPI
   * officiel de la société (champ kpiCode). */
  onOuvrirKpi?: (kpiId: string) => void;
};

/** Formate un nombre avec espaces (séparateur de milliers) et virgule décimale */
function fmtComposant(valeur: number, unite: string): string {
  return formatValeurReelle(valeur, unite);
}

/**
 * Modal plein écran affichant le PDF source à la page du KPI sélectionné.
 * Le bouton "Corriger" envoie via le callback onCorrection (hook parent).
 */
export function KpiPdfModal({ kpiId, label, kpi, societe, onClose, onCorrection, validationHumaine, onValidation, onOuvrirKpi }: Props) {
  // Décision 145 — un KPI peut avoir son propre PDF source (ex. une
  // valeur avertissement venant d'un 2e document), prioritaire sur le
  // PDF par défaut de la société.
  // Décision 158 — un composant de KPI calculé peut être sur un autre PDF :
  // pdfCourant suit le document de la page affichée.
  const [pdfCourant, setPdfCourant] = useState(kpi.sourcePdf ?? PDF_PAR_SOCIETE[societe]);
  const pdfUrl = pdfCourant ? `/api/pdf/${encodeURIComponent(pdfCourant)}` : null;

  // --- Navigation page PDF ---
  // viewingPage contrôle quelle page le PDF viewer affiche.
  // viewKey force un remount du PdfPageViewer pour changer de page.
  const [viewingPage, setViewingPage] = useState(kpi.pageSource ?? 1);
  const [viewKey, setViewKey] = useState(0);

  /** `pdf` absent : même document (composants « somme ») ; null : PDF par
   * défaut de la société (composants de KPI calculé, Décision 158). */
  function naviguerVersPage(page: number, pdf?: string | null) {
    if (pdf !== undefined) setPdfCourant(pdf ?? PDF_PAR_SOCIETE[societe]);
    setViewingPage(page);
    setViewKey((k) => k + 1);
  }

  // KPI calculé (Décision 158) : règle, composants et recalcul en direct.
  const formule = kpi.formule ?? null;

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

  // --- Validation humaine ---
  const [validationEnCours, setValidationEnCours] = useState(false);
  const [dejaValide, setDejaValide] = useState(!!validationHumaine);

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

  // « Source : » en français simple quand il existe (KPIs à avertissement).
  const chapitre = kpi.sourceLisible ?? kpi.chapitreSource;
  const source =
    chapitre && kpi.pageSource
      ? `${chapitre}, p. ${kpi.pageSource}`
      : chapitre ?? (kpi.pageSource ? `p. ${kpi.pageSource}` : null);

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
                <h3 className="font-heading text-lg text-text-primary truncate">{kpi.libelle ?? label}</h3>
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
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium flex-shrink-0 text-blue-700 bg-blue-50">
                    <Calculator className="w-3 h-3" />
                    Valeur calculée
                  </span>
                )}
              </div>
              <p className="text-xs text-text-tertiary mt-0.5 truncate">
                {societe}
                {source ? ` · Source : ${source}` : ""}
              </p>
              {kpi.avertissement && (
                <p role="note" className="mt-1.5 flex items-start gap-1.5 text-xs leading-snug text-text-secondary">
                  <Scale className="w-3.5 h-3.5 mt-px flex-shrink-0 text-accent" aria-hidden="true" />
                  <span>
                    <span className="font-medium text-accent">Valeur non comparable.</span>{" "}
                    {kpi.noteAvertissement?.trim() ||
                      "Valeur calculée sur une base non directement comparable aux autres sociétés."}
                  </span>
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            {/* Valeur extraite mise en évidence */}
            <div className="hidden sm:flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-1.5">
              <span className="text-xs text-text-tertiary">{formule ? "Valeur calculée :" : "Valeur extraite :"}</span>
              <span className="font-mono text-base font-bold text-text-primary">
                {formatValeurBrute(kpi.valeurBrute, kpi.uniteBrute, kpi.valeur, kpi.unite, DECIMALES_KPIS[kpiId])}
              </span>
              {/* Une valeur calculée se corrige par ses composants, pas directement. */}
              {!formule && (
                <button
                  onClick={() => setShowCorrection(!showCorrection)}
                  className="ml-1 w-7 h-7 flex items-center justify-center rounded-md text-text-tertiary hover:text-accent hover:bg-accent/10 transition-colors"
                  title="Corriger cette valeur"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
              )}
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

            {/* Bouton validation humaine */}
            {onValidation && (
              dejaValide ? (
                <span
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-emerald-700 bg-emerald-50 border border-emerald-200"
                  title={validationHumaine ? `Traité par ${validationHumaine.par} le ${new Date(validationHumaine.date).toLocaleDateString("fr-FR")}` : "Traité par un humain"}
                >
                  <UserCheck className="w-4 h-4" />
                  Traité
                </span>
              ) : (
                <button
                  onClick={async () => {
                    setValidationEnCours(true);
                    const ok = await onValidation(societe, kpiId);
                    if (ok) setDejaValide(true);
                    setValidationEnCours(false);
                  }}
                  disabled={validationEnCours}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-text-secondary border border-border hover:text-emerald-700 hover:bg-emerald-50 hover:border-emerald-200 transition-colors disabled:opacity-50"
                  title="Marquer ce KPI comme vérifié par un humain"
                >
                  {validationEnCours ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  Marquer traité
                </button>
              )
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

        {/* Contenu scrollable — tout défile ensemble */}
        <div className="flex-1 overflow-y-auto">

        {/* Valeur sur mobile */}
        <div className="sm:hidden flex items-center gap-2 px-4 py-2 border-b border-border bg-surface">
          <span className="text-xs text-text-tertiary">{formule ? "Valeur calculée :" : "Valeur extraite :"}</span>
          <span className="font-mono text-base font-bold text-text-primary">
            {formatValeurBrute(kpi.valeurBrute, kpi.uniteBrute, kpi.valeur, kpi.unite, DECIMALES_KPIS[kpiId])}
          </span>
          {!formule && (
            <button
              onClick={() => setShowCorrection(!showCorrection)}
              className="ml-1 w-7 h-7 flex items-center justify-center rounded-md text-text-tertiary hover:text-accent hover:bg-accent/10 transition-colors"
              title="Corriger cette valeur"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
          )}
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

        {/* KPI calculé (Décision 158) : règle, composants, recalcul en direct */}
        {hasComposants && formule && (
          <DecompositionFormule
            kpi={kpi}
            decimales={DECIMALES_KPIS[kpiId]}
            ouverte={showDecomposition}
            onBasculer={() => setShowDecomposition(!showDecomposition)}
            onPage={naviguerVersPage}
            onOuvrirKpi={onOuvrirKpi}
          />
        )}

        {/* Section décomposition — KPIs composés (somme), inchangée */}
        {hasComposants && !formule && (
          <div className="border-b border-border bg-slate-50/50 flex-shrink-0">
            <button
              onClick={() => setShowDecomposition(!showDecomposition)}
              className="w-full flex items-center gap-2 px-4 sm:px-5 py-2 text-left hover:bg-slate-100/50 transition-colors"
            >
              <Calculator className="w-4 h-4 text-blue-600 flex-shrink-0" />
              <span className="text-sm font-medium text-slate-700">Décomposition</span>
              <span className="text-xs text-blue-500">
                ({kpi.composants!.length} composant{kpi.composants!.length > 1 ? "s" : ""})
              </span>
              <svg
                className={`w-4 h-4 text-slate-400 ml-auto transition-transform ${showDecomposition ? "rotate-180" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showDecomposition && (
              <div className="px-4 sm:px-5 pb-3 space-y-2">
                {kpi.composants!.map((comp, i) => (
                  <div key={i}>
                    {i > 0 && (
                      <div className="flex items-center gap-2 py-1 pl-3">
                        <span className="text-sm font-mono font-bold text-blue-600">
                          {comp.operation === "-" ? "−" : "+"}
                        </span>
                      </div>
                    )}
                    <button
                      onClick={() => comp.pageSource && naviguerVersPage(comp.pageSource)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white border border-slate-300 hover:border-blue-400 hover:bg-blue-50 transition-colors group text-left shadow-sm"
                    >
                      <span className="font-mono text-xs font-semibold text-white bg-blue-600 px-2 py-1 rounded flex-shrink-0">
                        {comp.codeQrt}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-900 truncate">{comp.label}</p>
                        <p className="text-sm text-slate-600 mt-0.5">
                          <span className="font-mono font-semibold text-slate-800">{fmtComposant(comp.valeur, comp.unite)}</span>
                          {comp.pageSource != null && (
                            <span className="text-blue-600 group-hover:underline ml-2">
                              p.&nbsp;{comp.pageSource}
                            </span>
                          )}
                        </p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-colors flex-shrink-0" />
                    </button>
                  </div>
                ))}

                <div className="flex items-center gap-3 px-3 pt-2.5 mt-1.5 border-t-2 border-slate-300">
                  <span className="text-sm font-bold text-blue-700">Total</span>
                  <span className="font-mono text-base font-bold text-slate-900">
                    {fmtComposant(
                      kpi.composants!.reduce((acc, c) => acc + (c.operation === "-" ? -c.valeur : c.valeur), 0),
                      kpi.unite
                    )}
                  </span>
                  <span className="text-xs text-slate-500 ml-auto">
                    Valeur stockée : {formatValeurReelle(kpi.valeur, kpi.unite)}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* PDF viewer */}
        <div className="h-[80vh]">
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
        </div>{/* fin contenu scrollable */}
      </div>
    </div>
  );
}

/**
 * Décision 158 — détail d'un KPI calculé : règle en clair, composants
 * (numérateur / dénominateur pour un ratio, termes +/− pour une différence),
 * page source cliquable (sur le bon PDF), lien vers le KPI officiel quand le
 * composant en est un, puis recalcul en direct comparé à la valeur affichée.
 * Couleurs neutres (accent) : aucun feu tricolore.
 */
function DecompositionFormule({
  kpi,
  decimales,
  ouverte,
  onBasculer,
  onPage,
  onOuvrirKpi,
}: {
  kpi: KpiExtrait;
  decimales?: number;
  ouverte: boolean;
  onBasculer: () => void;
  onPage: (page: number, pdf?: string | null) => void;
  onOuvrirKpi?: (kpiId: string) => void;
}) {
  const formule = kpi.formule!;
  const composants = kpi.composants ?? [];
  const recalcul = recalculerKpi(kpi);
  const coherent = recalcul !== null && Math.abs(recalcul - kpi.valeur) <= TOLERANCE_RECALCUL + 1e-9;
  const ratio = formule.type === "ratio";
  const groupes = ratio
    ? [
        { titre: "Numérateur", items: composants.filter((c) => c.operation === "num") },
        { titre: "Dénominateur", items: composants.filter((c) => c.operation === "den") },
      ]
    : [{ titre: null, items: composants }];

  return (
    <div className="border-b border-border bg-surface-secondary/50 flex-shrink-0">
      <button
        onClick={onBasculer}
        aria-expanded={ouverte}
        className="w-full flex items-center gap-2 px-4 sm:px-5 py-2 text-left hover:bg-surface-hover transition-colors"
      >
        <Calculator className="w-4 h-4 text-accent flex-shrink-0" aria-hidden="true" />
        <span className="text-sm font-medium text-text-primary">Règle de calcul</span>
        <span className="text-xs text-text-tertiary">
          ({composants.length} composant{composants.length > 1 ? "s" : ""})
        </span>
        <svg
          className={`w-4 h-4 text-text-tertiary ml-auto transition-transform ${ouverte ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {ouverte && (
        <div className="px-4 sm:px-5 pb-3 space-y-3">
          <p className="text-sm font-medium text-text-primary">{formule.texte}</p>

          {groupes.map((g) => (
            <div key={g.titre ?? "termes"} className="space-y-1.5">
              {g.titre && (
                <p className="text-[11px] font-bold uppercase tracking-wide text-text-tertiary">
                  {g.titre}
                  {g.items.length > 1 && <span className="font-medium normal-case tracking-normal"> · somme</span>}
                </p>
              )}
              {g.items.map((c, i) => {
                // Ratio : somme des termes, le signe de la valeur devient l'opérateur.
                // Différence : l'opérateur est celui du composant.
                const operateur = ratio
                  ? i === 0
                    ? c.valeur < 0
                      ? "−"
                      : ""
                    : c.valeur < 0
                      ? "−"
                      : "+"
                  : c.operation === "-"
                    ? "−"
                    : i === 0
                      ? ""
                      : "+";
                const valeurAffichee = operateur === "−" ? Math.abs(c.valeur) : c.valeur;
                return (
                  <LigneComposant
                    key={i}
                    composant={c}
                    operateur={operateur}
                    valeurAffichee={valeurAffichee}
                    onPage={onPage}
                    onOuvrirKpi={onOuvrirKpi}
                  />
                );
              })}
            </div>
          ))}

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-2.5 border-t border-border">
            <span className="font-mono text-base font-bold text-text-primary">
              = {recalcul !== null ? formatValeurReelle(recalcul, kpi.unite, decimales) : "—"}
            </span>
            {coherent ? (
              <span className="inline-flex items-center gap-1 text-xs text-text-secondary">
                <CheckCircle2 className="w-3.5 h-3.5 text-accent flex-shrink-0" aria-hidden="true" />
                cohérent avec la valeur affichée ({formatValeurReelle(kpi.valeur, kpi.unite, decimales)})
              </span>
            ) : (
              <span role="note" className="inline-flex items-start gap-1 text-xs text-text-secondary">
                <Info className="w-3.5 h-3.5 mt-px text-text-tertiary flex-shrink-0" aria-hidden="true" />
                Le recalcul s&apos;écarte de la valeur affichée ({formatValeurReelle(kpi.valeur, kpi.unite, decimales)}) :
                valeur à vérifier.
              </span>
            )}
          </div>

          {formule.note && (
            <p className="flex items-start gap-1.5 text-xs leading-relaxed text-text-secondary">
              <Info className="w-3.5 h-3.5 mt-px text-text-tertiary flex-shrink-0" aria-hidden="true" />
              <span>{formule.note}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function LigneComposant({
  composant: c,
  operateur,
  valeurAffichee,
  onPage,
  onOuvrirKpi,
}: {
  composant: Composant;
  operateur: string;
  valeurAffichee: number;
  onPage: (page: number, pdf?: string | null) => void;
  onOuvrirKpi?: (kpiId: string) => void;
}) {
  const page = c.pageSource;
  const kpiCode = c.kpiCode;
  return (
    <div className="flex items-start gap-2">
      <span className="w-4 flex-shrink-0 pt-2 text-center font-mono text-sm font-bold text-accent" aria-hidden="true">
        {operateur}
      </span>
      <div className="flex-1 min-w-0 rounded-lg border border-border bg-surface px-3 py-2">
        <div className="flex items-start gap-2">
          {c.codeQrt && (
            <span className="font-mono text-[11px] font-semibold text-accent bg-accent-light px-1.5 py-0.5 rounded flex-shrink-0">
              {c.codeQrt}
            </span>
          )}
          <p className="text-sm font-medium text-text-primary min-w-0">{c.label}</p>
        </div>
        {c.detail && <p className="text-xs font-mono text-text-tertiary mt-0.5 break-words">{c.detail}</p>}
        <div className="flex items-center gap-x-3 gap-y-1 flex-wrap mt-1">
          <span className="font-mono text-sm font-semibold text-text-primary">
            {operateur === "−" && <span className="sr-only">moins </span>}
            {formatValeurReelle(valeurAffichee, c.unite)}
          </span>
          {page != null && (
            <button
              type="button"
              onClick={() => onPage(page, c.sourcePdf)}
              className="inline-flex items-center gap-1 text-xs text-accent hover:underline"
              title="Afficher cette page du PDF"
            >
              p.&nbsp;{page}
              <ArrowRight className="w-3 h-3" aria-hidden="true" />
            </button>
          )}
          {kpiCode && onOuvrirKpi && (
            <button
              type="button"
              onClick={() => onOuvrirKpi(kpiCode)}
              className="text-xs text-accent hover:underline text-left"
              title="Ouvrir le détail de ce KPI"
            >
              Voir le KPI « {labelKpi(kpiCode)} »
            </button>
          )}
          {c.valide !== undefined && (
            <span className="inline-flex items-center gap-1 text-[11px] text-text-tertiary">
              {c.valide && <ShieldCheck className="w-3 h-3" aria-hidden="true" />}
              {c.valide ? "vérifié" : "non vérifié"}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
