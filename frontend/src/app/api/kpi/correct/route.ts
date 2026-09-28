import { NextResponse } from "next/server";

export const runtime = "nodejs";

// ---------------------------------------------------------------------------
// Stockage Vercel Blob — utilisé en production (Vercel) pour persister les
// corrections KPI dans un fichier JSON hébergé dans le store Blob déjà
// configuré pour les PDFs. En local, on délègue au script Python/SQLite.
// ---------------------------------------------------------------------------
const CORRECTIONS_BLOB_KEY = "kpi-corrections/corrections.json";

type Correction = {
  valeurCorrigee: string;
  commentaire: string | null;
  date: string;
};
type CorrectionsMap = Record<string, Correction>; // clé = "societe::kpiId"

async function lireCorrectionsBlob(): Promise<CorrectionsMap> {
  const { get } = await import("@vercel/blob");
  try {
    const result = await get(CORRECTIONS_BLOB_KEY, { access: "private" });
    if (!result || result.statusCode !== 200 || !result.stream) return {};
    const reader = result.stream.getReader();
    const chunks: Uint8Array[] = [];
    let done = false;
    while (!done) {
      const r = await reader.read();
      done = r.done;
      if (r.value) chunks.push(r.value);
    }
    const texte = new TextDecoder().decode(Buffer.concat(chunks));
    return JSON.parse(texte) as CorrectionsMap;
  } catch {
    return {};
  }
}

async function ecrireCorrectionsBlob(corrections: CorrectionsMap): Promise<void> {
  const { put } = await import("@vercel/blob");
  const contenu = JSON.stringify(corrections, null, 2);
  await put(CORRECTIONS_BLOB_KEY, contenu, {
    access: "private",
    contentType: "application/json",
    addRandomSuffix: false,
  });
}

// ---------------------------------------------------------------------------
// Fallback local : appel du script Python/SQLite (corriger_kpi.py)
// ---------------------------------------------------------------------------
async function corrigerViaScript(
  societe: string,
  kpiId: string,
  valeurCorrigee: string,
  commentaire: string | null
): Promise<{ ok: boolean; erreur?: string; [k: string]: unknown }> {
  const { execFile } = await import("node:child_process");
  const { promisify } = await import("node:util");
  const path = await import("node:path");
  const execFileAsync = promisify(execFile);

  const RACINE_DEPOT = process.env.SFCR_REPO_ROOT ?? path.join(process.cwd(), "..");
  const SCRIPT = process.env.SFCR_SCRIPT_CORRECTION ?? path.join(RACINE_DEPOT, "corriger_kpi.py");
  const PYTHON = process.env.SFCR_PYTHON_BIN_LEGER ?? "python";

  const args = [SCRIPT, "--societe", societe, "--kpi-name", kpiId, "--valeur-corrigee", valeurCorrigee];
  if (commentaire) args.push("--commentaire", commentaire);

  const { stdout } = await execFileAsync(PYTHON, args, { cwd: RACINE_DEPOT });
  return JSON.parse(stdout.trim());
}

// ---------------------------------------------------------------------------
// GET — Retourne toutes les corrections enregistrées (Vercel Blob)
// ---------------------------------------------------------------------------
export async function GET() {
  if (!process.env.VERCEL) {
    // En local, pas de Blob — les corrections sont dans SQLite, pas
    // d'endpoint GET pour l'instant (le JSON est régénéré manuellement).
    return NextResponse.json({ corrections: {} });
  }

  try {
    const corrections = await lireCorrectionsBlob();
    return NextResponse.json({ corrections });
  } catch (err) {
    return NextResponse.json(
      { corrections: {}, erreur: err instanceof Error ? err.message : String(err) },
      { status: 500 }
    );
  }
}

// ---------------------------------------------------------------------------
// POST — Enregistre une correction
// ---------------------------------------------------------------------------
type CorpsRequete = {
  societe?: string;
  kpiId?: string;
  valeurCorrigee?: string;
  commentaire?: string | null;
};

export async function POST(request: Request) {
  let corps: CorpsRequete;
  try {
    corps = (await request.json()) as CorpsRequete;
  } catch {
    return NextResponse.json({ ok: false, erreur: "Requête invalide." }, { status: 400 });
  }

  const { societe, kpiId, valeurCorrigee, commentaire } = corps;
  if (!societe || typeof societe !== "string" || !societe.trim()) {
    return NextResponse.json({ ok: false, erreur: "Société manquante." }, { status: 400 });
  }
  if (!kpiId || typeof kpiId !== "string" || !kpiId.trim()) {
    return NextResponse.json({ ok: false, erreur: "kpiId manquant." }, { status: 400 });
  }
  if (!valeurCorrigee || typeof valeurCorrigee !== "string" || !valeurCorrigee.trim()) {
    return NextResponse.json({ ok: false, erreur: "Valeur corrigée manquante." }, { status: 400 });
  }

  // --- Mode Vercel : Blob ---
  if (process.env.VERCEL) {
    try {
      const corrections = await lireCorrectionsBlob();
      const cle = `${societe.trim()}::${kpiId.trim()}`;
      corrections[cle] = {
        valeurCorrigee: valeurCorrigee.trim(),
        commentaire: (commentaire && typeof commentaire === "string" && commentaire.trim()) || null,
        date: new Date().toISOString(),
      };
      await ecrireCorrectionsBlob(corrections);
      return NextResponse.json({ ok: true });
    } catch (err) {
      return NextResponse.json(
        { ok: false, erreur: `Échec Blob : ${err instanceof Error ? err.message : String(err)}` },
        { status: 500 }
      );
    }
  }

  // --- Mode local : script Python/SQLite ---
  try {
    const resultat = await corrigerViaScript(
      societe.trim(),
      kpiId.trim(),
      valeurCorrigee.trim(),
      (commentaire && typeof commentaire === "string" && commentaire.trim()) || null
    );
    if (!resultat.ok) {
      return NextResponse.json(resultat, { status: 400 });
    }
    return NextResponse.json(resultat);
  } catch (err) {
    return NextResponse.json(
      { ok: false, erreur: `Échec correction : ${err instanceof Error ? err.message : String(err)}` },
      { status: 500 }
    );
  }
}
