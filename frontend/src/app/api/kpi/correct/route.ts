import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

const execFileAsync = promisify(execFile);

// Racine du dépôt (rag-actuariat/), un niveau au-dessus de frontend/ — même
// convention que /api/upload-pdf et /api/lancer-extraction.
const RACINE_DEPOT = process.env.SFCR_REPO_ROOT ?? path.join(process.cwd(), "..");
const SCRIPT_CORRECTION =
  process.env.SFCR_SCRIPT_CORRECTION ?? path.join(RACINE_DEPOT, "corriger_kpi.py");
// corriger_kpi.py n'utilise que sqlite3 (stdlib) — contrairement à
// extraire_un_pdf.py, n'a pas besoin du venv Docling/PyMuPDF/PaddleOCR.
// "python" (pas "python3") : plus fiable sur PATH Windows, cf. Décision 111.
const PYTHON_BIN = process.env.SFCR_PYTHON_BIN_LEGER ?? "python";

type CorpsRequete = {
  societe?: string;
  kpiId?: string;
  valeurCorrigee?: string;
  commentaire?: string | null;
};

type ResultatScript =
  | { ok: true; ancienneValeur: number | null; nouvelleValeur: number; nouveauRawValue: number | null }
  | { ok: false; erreur: string };

/**
 * Applique une correction manuelle sur un KPI (bouton "Corriger" du modal
 * KPI, onglet Données). Synchrone (pas de job en arrière-plan comme
 * /api/lancer-extraction) : le frontend attend { ok: true } avant de
 * fermer le formulaire.
 *
 * N'écrit PAS automatiquement les JSON frontend après correction (Option B,
 * Décision 111) — il faut relancer `npm run regenerate-json` (racine du
 * dépôt) pour que donnees-extraites.json reflète la correction.
 *
 * Comme le reste des routes qui touchent kpis.db, ne fonctionne qu'en
 * local (accès filesystem direct à la DB SQLite, pas de DB en prod Vercel).
 */
export async function POST(request: Request) {
  let corps: CorpsRequete;
  try {
    corps = (await request.json()) as CorpsRequete;
  } catch {
    return NextResponse.json({ ok: false, erreur: "Requête invalide." }, { status: 400 });
  }

  const { societe, kpiId, valeurCorrigee, commentaire } = corps;
  if (!societe || typeof societe !== "string" || societe.trim().length < 1) {
    return NextResponse.json({ ok: false, erreur: "Société manquante." }, { status: 400 });
  }
  if (!kpiId || typeof kpiId !== "string" || kpiId.trim().length < 1) {
    return NextResponse.json({ ok: false, erreur: "kpiId manquant." }, { status: 400 });
  }
  if (!valeurCorrigee || typeof valeurCorrigee !== "string" || valeurCorrigee.trim().length < 1) {
    return NextResponse.json({ ok: false, erreur: "Valeur corrigée manquante." }, { status: 400 });
  }

  const args = [
    SCRIPT_CORRECTION,
    "--societe",
    societe.trim(),
    "--kpi-name",
    kpiId.trim(),
    "--valeur-corrigee",
    valeurCorrigee.trim(),
  ];
  if (commentaire && typeof commentaire === "string" && commentaire.trim()) {
    args.push("--commentaire", commentaire.trim());
  }

  try {
    const { stdout } = await execFileAsync(PYTHON_BIN, args, { cwd: RACINE_DEPOT });
    const resultat = JSON.parse(stdout.trim()) as ResultatScript;
    if (!resultat.ok) {
      return NextResponse.json(resultat, { status: 400 });
    }
    return NextResponse.json(resultat);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { ok: false, erreur: `Échec de la correction : ${message}` },
      { status: 500 }
    );
  }
}
