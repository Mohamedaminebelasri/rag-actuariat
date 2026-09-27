import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

const RACINE_DEPOT = process.env.SFCR_REPO_ROOT ?? path.join(process.cwd(), "..");
const DOSSIER_JOBS = process.env.SFCR_JOBS_DIR ?? path.join(RACINE_DEPOT, "jobs");

// Un id de job est un UUID généré par /api/lancer-extraction (crypto.randomUUID) :
// on le valide avant de construire un chemin de fichier avec, pour ne jamais
// lire en dehors de jobs/ à partir d'un paramètre d'URL.
const FORME_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Suivi d'une extraction en cours (déclenchée par /api/lancer-extraction) :
 * relit simplement jobs/<id>.json à chaque appel — le frontend interroge
 * cette route toutes les quelques secondes pendant l'extraction.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  if (!FORME_UUID.test(id)) {
    return NextResponse.json({ ok: false, erreur: "Identifiant de job invalide." }, { status: 400 });
  }

  try {
    const brut = await readFile(path.join(DOSSIER_JOBS, `${id}.json`), "utf-8");
    const statut = JSON.parse(brut);
    return NextResponse.json({ ok: true, ...statut });
  } catch (err) {
    const code = (err as NodeJS.ErrnoException).code;
    if (code === "ENOENT") {
      return NextResponse.json({ ok: false, erreur: "Ce job n'existe pas (ou plus)." }, { status: 404 });
    }
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ ok: false, erreur: `Lecture du statut impossible : ${message}` }, { status: 500 });
  }
}
