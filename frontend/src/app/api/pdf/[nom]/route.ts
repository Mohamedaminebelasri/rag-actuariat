import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { get } from "@vercel/blob";

export const runtime = "nodejs";

// data/ est à la racine du dépôt (rag-actuariat/), un niveau au-dessus
// de frontend/. Surchargeable pour les tests.
const DOSSIER_DATA = process.env.SFCR_DATA_DIR ?? path.join(process.cwd(), "..", "data");

// Préfixe utilisé dans Vercel Blob pour tous les PDF SFCR (voir
// scripts/migrer-pdfs-vers-blob.mjs). Sur Vercel, data/ n'existe pas
// (système de fichiers éphémère) : on sert depuis Blob à la place.
const PREFIXE_BLOB = "sfcr/";

/**
 * Sert un PDF pour affichage dans l'onglet Documents.
 *
 * - En local (npm run dev / next start) : lu directement depuis data/,
 *   comme avant — aucun changement de comportement pour la démo.
 * - Sur Vercel (process.env.VERCEL) : lu depuis Vercel Blob (store privé
 *   "sfcr-pdfs") via get() — jamais d'URL Blob exposée directement au
 *   navigateur, on la fait transiter par cette route.
 *
 * IMPORTANT — sécurité : le nom vient de l'URL, donc :
 *  - on refuse tout ce qui contient un séparateur de chemin ou "..",
 *  - on ne concatène jamais le nom brut avec DOSSIER_DATA sans passer
 *    par path.basename et vérifier que le chemin résolu reste sous
 *    DOSSIER_DATA (défense en profondeur au cas où path.basename change).
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

  if (process.env.VERCEL) {
    return servirDepuisBlob(nomSain);
  }
  return servirDepuisDisque(nomSain);
}

async function servirDepuisBlob(nomSain: string): Promise<Response> {
  try {
    const resultat = await get(`${PREFIXE_BLOB}${nomSain}`, { access: "private" });
    if (!resultat || resultat.statusCode !== 200 || !resultat.stream) {
      return NextResponse.json(
        { erreur: `PDF introuvable dans le stockage en ligne : ${nomSain}.` },
        { status: 404 }
      );
    }
    return new Response(resultat.stream, {
      status: 200,
      headers: {
        "Content-Type": resultat.blob.contentType || "application/pdf",
        "Cache-Control": "public, max-age=3600, must-revalidate",
        "Content-Disposition": `inline; filename="${encodeURIComponent(nomSain)}"`,
      },
    });
  } catch (err) {
    return NextResponse.json(
      { erreur: err instanceof Error ? err.message : String(err) },
      { status: 500 }
    );
  }
}

async function servirDepuisDisque(nomSain: string): Promise<Response> {
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
