import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { get, head } from "@vercel/blob";

export const runtime = "nodejs";

// data/ est à la racine du dépôt (rag-actuariat/), un niveau au-dessus
// de frontend/. Surchargeable pour les tests.
const DOSSIER_DATA = process.env.SFCR_DATA_DIR ?? path.join(process.cwd(), "..", "data");

// Préfixe utilisé dans Vercel Blob pour tous les PDF SFCR (voir
// scripts/migrer-pdfs-vers-blob.mjs). Sur Vercel, data/ n'existe pas
// (système de fichiers éphémère) : on sert depuis Blob à la place.
const PREFIXE_BLOB = "sfcr/";

// Cache longue durée : les PDF SFCR ne changent jamais une fois uploadés.
// 7 jours + immutable : le navigateur ne revalide pas pendant cette durée.
const CACHE_HEADER = "public, max-age=604800, immutable";

/**
 * Sert un PDF pour affichage dans l'onglet Documents.
 *
 * Supporte les requêtes Range (HTTP 206 Partial Content) pour que
 * pdfjs-dist puisse charger seulement les pages demandées au lieu de
 * télécharger tout le fichier (~20 Mo pour Aéma). Cela réduit le temps
 * de chargement initial de plusieurs secondes à < 1 seconde.
 *
 * - En local (npm run dev / next start) : lu directement depuis data/.
 * - Sur Vercel (process.env.VERCEL) : lu depuis Vercel Blob.
 *
 * IMPORTANT — sécurité : le nom vient de l'URL, donc :
 *  - on refuse tout ce qui contient un séparateur de chemin ou "..",
 *  - on ne concatène jamais le nom brut avec DOSSIER_DATA sans passer
 *    par path.basename et vérifier que le chemin résolu reste sous
 *    DOSSIER_DATA (défense en profondeur au cas où path.basename change).
 */
export async function GET(request: Request, { params }: { params: Promise<{ nom: string }> }) {
  const { nom } = await params;

  const nomDecode = decodeURIComponent(nom);
  if (nomDecode.includes("/") || nomDecode.includes("\\") || nomDecode.includes("..")) {
    return NextResponse.json({ erreur: "Nom de fichier invalide." }, { status: 400 });
  }
  const nomSain = path.basename(nomDecode);
  if (!nomSain.toLowerCase().endsWith(".pdf")) {
    return NextResponse.json({ erreur: "Seuls les fichiers PDF sont servis." }, { status: 400 });
  }

  const rangeHeader = request.headers.get("Range");

  if (process.env.VERCEL) {
    return servirDepuisBlob(nomSain, rangeHeader);
  }
  return servirDepuisDisque(nomSain, rangeHeader);
}

/**
 * Parse un header Range simple (ex: "bytes=100-200" ou "bytes=100-").
 * Ne gère que le premier range (suffisant pour pdfjs-dist).
 */
function parseRange(rangeHeader: string, tailleFichier: number): { start: number; end: number } | null {
  const match = rangeHeader.match(/^bytes=(\d+)-(\d*)$/);
  if (!match) return null;
  const start = parseInt(match[1], 10);
  const end = match[2] ? parseInt(match[2], 10) : tailleFichier - 1;
  if (start > end || start >= tailleFichier) return null;
  return { start, end: Math.min(end, tailleFichier - 1) };
}

async function servirDepuisBlob(nomSain: string, rangeHeader: string | null): Promise<Response> {
  try {
    // Si range request → on doit d'abord connaître la taille, puis
    // télécharger la plage via fetch avec Range sur l'URL du blob.
    if (rangeHeader) {
      // head() donne les métadonnées sans télécharger le contenu
      const meta = await head(`${PREFIXE_BLOB}${nomSain}`);
      if (!meta) {
        return NextResponse.json(
          { erreur: `PDF introuvable dans le stockage en ligne : ${nomSain}.` },
          { status: 404 }
        );
      }
      const taille = meta.size;
      const range = parseRange(rangeHeader, taille);
      if (!range) {
        return new Response(null, {
          status: 416,
          headers: { "Content-Range": `bytes */${taille}` },
        });
      }

      // Fetch la plage depuis l'URL Blob (Vercel Blob supporte Range nativement)
      const blobReponse = await fetch(meta.downloadUrl, {
        headers: { Range: `bytes=${range.start}-${range.end}` },
      });

      return new Response(blobReponse.body, {
        status: 206,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Range": `bytes ${range.start}-${range.end}/${taille}`,
          "Content-Length": String(range.end - range.start + 1),
          "Accept-Ranges": "bytes",
          "Cache-Control": CACHE_HEADER,
          "Content-Disposition": `inline; filename="${encodeURIComponent(nomSain)}"`,
        },
      });
    }

    // Pas de range → réponse complète (comportement existant)
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
        "Content-Length": String(resultat.blob.size),
        "Accept-Ranges": "bytes",
        "Cache-Control": CACHE_HEADER,
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

async function servirDepuisDisque(nomSain: string, rangeHeader: string | null): Promise<Response> {
  const cheminAbsolu = path.resolve(DOSSIER_DATA, nomSain);
  const racineAbsolue = path.resolve(DOSSIER_DATA);
  if (!cheminAbsolu.startsWith(racineAbsolue + path.sep)) {
    return NextResponse.json({ erreur: "Chemin refusé." }, { status: 400 });
  }

  try {
    const stats = await stat(cheminAbsolu);

    // Range request → réponse partielle (206)
    if (rangeHeader) {
      const range = parseRange(rangeHeader, stats.size);
      if (!range) {
        return new Response(null, {
          status: 416,
          headers: { "Content-Range": `bytes */${stats.size}` },
        });
      }

      const flux = createReadStream(cheminAbsolu, { start: range.start, end: range.end });
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
        status: 206,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Range": `bytes ${range.start}-${range.end}/${stats.size}`,
          "Content-Length": String(range.end - range.start + 1),
          "Accept-Ranges": "bytes",
          "Cache-Control": CACHE_HEADER,
          "Content-Disposition": `inline; filename="${encodeURIComponent(nomSain)}"`,
        },
      });
    }

    // Pas de range → réponse complète
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
        "Accept-Ranges": "bytes",
        "Cache-Control": CACHE_HEADER,
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
