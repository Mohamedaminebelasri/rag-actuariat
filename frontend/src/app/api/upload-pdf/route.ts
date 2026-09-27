import { access, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { nomFichierSur } from "@/lib/pdf-titre";

export const runtime = "nodejs";

// data/ est à la racine du dépôt (rag-actuariat/data/), un niveau au-dessus
// de frontend/ (où tourne ce serveur Next.js). Surchargeable par variable
// d'environnement — utile pour les tests, sans toucher au vrai dossier.
const DOSSIER_DATA = process.env.SFCR_DATA_DIR ?? path.join(process.cwd(), "..", "data");

async function existe(chemin: string): Promise<boolean> {
  try {
    await access(chemin);
    return true;
  } catch {
    return false;
  }
}

/** Ajoute " (2)", " (3)"... avant l'extension si le nom existe déjà —
 * jamais d'écrasement silencieux d'un PDF existant. */
async function nomSansCollision(nomFichier: string): Promise<string> {
  const ext = path.extname(nomFichier);
  const base = nomFichier.slice(0, -ext.length);
  let candidat = nomFichier;
  let i = 2;
  while (await existe(path.join(DOSSIER_DATA, candidat))) {
    candidat = `${base} (${i})${ext}`;
    i += 1;
  }
  return candidat;
}

/**
 * Étape 1 (dépôt de PDF) — appelée après confirmation du titre par
 * l'utilisateur. Enregistre le PDF dans data/ sous ce titre, prêt pour
 * l'étape suivante (extraction des KPIs), qui reste séparée et n'est pas
 * déclenchée ici.
 *
 * Ne fonctionne qu'en local (npm run dev / next start sur le PC) : sur un
 * déploiement serverless (Vercel), le système de fichiers n'est pas
 * persistant et cette route renverra une erreur claire plutôt que
 * d'échouer silencieusement.
 */
export async function POST(request: Request) {
  const forme = await request.formData();
  const fichier = forme.get("pdf");
  const titre = forme.get("titre");

  if (!(fichier instanceof File)) {
    return NextResponse.json({ ok: false, erreur: "Aucun fichier PDF reçu." }, { status: 400 });
  }
  if (typeof titre !== "string" || titre.trim().length < 3) {
    return NextResponse.json({ ok: false, erreur: "Le titre confirmé est trop court." }, { status: 400 });
  }

  try {
    await mkdir(DOSSIER_DATA, { recursive: true });
    const nomSouhaite = nomFichierSur(titre);
    const nomFinal = await nomSansCollision(nomSouhaite);
    const octets = Buffer.from(await fichier.arrayBuffer());
    await writeFile(path.join(DOSSIER_DATA, nomFinal), octets);

    return NextResponse.json({ ok: true, nomFichier: nomFinal, chemin: `data/${nomFinal}` });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const lectureSeuleProbable = /EROFS|EACCES|read-only/i.test(message);
    return NextResponse.json(
      {
        ok: false,
        erreur: lectureSeuleProbable
          ? "Écriture impossible : cette fonctionnalité nécessite de lancer le site en local (npm run dev), pas la version en ligne."
          : `Échec de l'enregistrement : ${message}`,
      },
      { status: 500 }
    );
  }
}
