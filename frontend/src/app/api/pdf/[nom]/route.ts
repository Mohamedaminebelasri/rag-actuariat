import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

// data/ est à la racine du dépôt (rag-actuariat/), un niveau au-dessus
// de frontend/. Surchargeable pour les tests.
const DOSSIER_DATA = process.env.SFCR_DATA_DIR ?? path.join(process.cwd(), "..", "data");

/**
 * Sert un PDF depuis data/ pour affichage dans l'onglet Documents.
 *
 * IMPORTANT — sécurité : le nom vient de l'URL, donc :
 *  - on refuse tout ce qui contient un séparateur de chemin ou "..",
 *  - on ne concatène jamais le nom brut avec DOSSIER_DATA sans passer
 *    par path.basename et vérifier que le chemin résolu reste sous
 *    DOSSIER_DATA (défense en profondeur au cas où path.basename change).
 *
 * Fonctionne uniquement en local (npm run dev / next start) : sur Vercel,
 * data/ n'est pas déployé (les PDF sont sur le PC).
 */
export async function GET(_request: Request, { params }: { params: Promise<{ nom: string }> }) {
  const { nom } = await params;

  const nomDecode = decodeURIComponent(nom);
  if (nomDecode.includes("/") || nomDecode.includes("\\") || nomDecode.includes("..")) {
    return NextResponse.json({ erreur: "Nom de fichier invalide." }, { status: 400 });
  }
  const nomSain = path.basename(nomDecode);
  if (!nomSain.toLowerCase().endsWith(".pdf")) {
    return NextResponse.json({ erreur: "Seuls les fichiers PDF sont servis." }, { status: 400 });
  }

  const cheminAbsolu = path.resolve(DOSSIER_DATA, nomSain);
  const racineAbsolue = path.resolve(DOSSIER_DATA);
  if (!cheminAbsolu.startsWith(racineAbsolue + path.sep)) {
    return NextResponse.json({ erreur: "Chemin refusé." }, { status: 400 });
  }

  try {
    const stats = await stat(cheminAbsolu);
    // Pour un gros PDF (jusqu'à ~22 Mo dans data/), on stream plutôt que
    // de charger en mémoire. Web ReadableStream construit à partir du
    // stream Node fs.
    const flux = createReadStream(cheminAbsolu);
    const corps = new ReadableStream({
      start(controller) {
        flux.on("data", (chunk) => controller.enqueue(chunk));
        flux.on("end", () => controller.close());
        flux.on("error", (err) => controller.error(err));
      },
      cancel() {
        flux.destroy();
      },
    });
    return new Response(corps, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Length": String(stats.size),
        // Cache 1h côté navigateur : les PDF ne bougent presque jamais,
        // et si un PDF est remplacé via l'onglet Upload il aura un nom
        // différent (jamais d'écrasement, voir nomSansCollision).
        "Cache-Control": "public, max-age=3600, must-revalidate",
        "Content-Disposition": `inline; filename="${encodeURIComponent(nomSain)}"`,
      },
    });
  } catch (err) {
    const code = (err as NodeJS.ErrnoException).code;
    if (code === "ENOENT") {
      return NextResponse.json(
        { erreur: `PDF introuvable : ${nomSain}. Lance le site en local pour y accéder.` },
        { status: 404 }
      );
    }
    return NextResponse.json(
      { erreur: err instanceof Error ? err.message : String(err) },
      { status: 500 }
    );
  }
}
