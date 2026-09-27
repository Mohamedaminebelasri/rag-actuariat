// Upload ponctuel des PDF de data/ vers Vercel Blob (store "sfcr-pdfs"),
// sous le prefixe "sfcr/". Idempotent : saute les fichiers deja presents
// dans Blob (meme taille), donc on peut relancer ce script autant de fois
// que necessaire (utile si l'upload complet depasse le temps imparti a un
// seul appel).
//
// Usage : depuis frontend/, avec BLOB_READ_WRITE_TOKEN dans l'environnement :
//   set -a; source .env.local; set +a; node scripts/migrer-pdfs-vers-blob.mjs

import { readdir, readFile, stat as statFs } from "node:fs/promises";
import path from "node:path";
import { put, list } from "@vercel/blob";

const DOSSIER_DATA = path.join(process.cwd(), "..", "data");
const PREFIXE_BLOB = "sfcr/";

async function main() {
  if (!process.env.BLOB_READ_WRITE_TOKEN) {
    console.error("BLOB_READ_WRITE_TOKEN manquant dans l'environnement.");
    process.exit(1);
  }

  const fichiers = (await readdir(DOSSIER_DATA)).filter((f) => f.toLowerCase().endsWith(".pdf"));

  // Deja presents dans Blob (avec leur taille, pour detecter un fichier
  // partiellement uploade ou remplace localement).
  const deja = new Map();
  let curseur;
  do {
    const page = await list({ prefix: PREFIXE_BLOB, cursor: curseur, limit: 1000 });
    for (const b of page.blobs) deja.set(b.pathname, b.size);
    curseur = page.hasMore ? page.cursor : undefined;
  } while (curseur);

  console.log(`${fichiers.length} PDF locaux, ${deja.size} deja dans Blob.`);

  let ok = 0;
  let sautes = 0;
  let echecs = 0;
  for (const fichier of fichiers) {
    const cheminBlob = `${PREFIXE_BLOB}${fichier}`;
    try {
      const tailleLocale = (await statFs(path.join(DOSSIER_DATA, fichier))).size;
      if (deja.get(cheminBlob) === tailleLocale) {
        sautes++;
        continue;
      }
      const contenu = await readFile(path.join(DOSSIER_DATA, fichier));
      const resultat = await put(cheminBlob, contenu, {
        access: "private",
        contentType: "application/pdf",
        allowOverwrite: true,
      });
      console.log(`OK  ${fichier} -> ${resultat.pathname}`);
      ok++;
    } catch (err) {
      console.error(`ECHEC ${fichier} :`, err instanceof Error ? err.message : err);
      echecs++;
    }
  }

  console.log(`\nTermine : ${ok} uploades, ${sautes} deja a jour, ${echecs} echecs sur ${fichiers.length}.`);
  if (echecs > 0) process.exit(1);
}

main();
