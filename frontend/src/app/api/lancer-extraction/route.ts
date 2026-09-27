import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import { mkdir, open, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

// Racine du dépôt (rag-actuariat/), un niveau au-dessus de frontend/.
// Mêmes surcharges par variable d'environnement que /api/upload-pdf, pour
// pouvoir tester sans toucher au vrai dépôt.
const RACINE_DEPOT = process.env.SFCR_REPO_ROOT ?? path.join(process.cwd(), "..");
const DOSSIER_JOBS = process.env.SFCR_JOBS_DIR ?? path.join(RACINE_DEPOT, "jobs");
const SCRIPT_EXTRACTION =
  process.env.SFCR_SCRIPT_EXTRACTION ?? path.join(RACINE_DEPOT, "extraire_un_pdf.py");
// Docling/PyMuPDF/PaddleOCR ne sont installés que dans ce venv (confirmé par
// Claude Code, 27/09 au soir) — le python système ne les a pas.
const PYTHON_BIN =
  process.env.SFCR_PYTHON_BIN ?? path.join(RACINE_DEPOT, "test_markdrop", ".venv", "Scripts", "python.exe");

type CorpsRequete = {
  chemin?: string; // ex. "data/mon-rapport.pdf" (renvoyé par /api/upload-pdf)
  nomFichier?: string;
  societe?: string;
  annee?: number;
};

async function ecrireStatutInitial(jobId: string, societe: string, annee: number) {
  const contenu = {
    statut: "en_cours",
    etape: "demarrage",
    message: "Lancement de l'extraction…",
    societe,
    annee,
    kpis: [],
    erreur: null,
  };
  await writeFile(path.join(DOSSIER_JOBS, `${jobId}.json`), JSON.stringify(contenu, null, 2));
}

/** Ne marque le job en erreur que s'il n'a pas déjà reçu un statut final —
 * évite d'écraser un résultat légitime arrivé juste avant la sortie du
 * process (course entre l'événement "exit" et la dernière écriture du
 * script Python). */
async function marquerErreurSiPasDeja(jobId: string, message: string) {
  const cheminJob = path.join(DOSSIER_JOBS, `${jobId}.json`);
  try {
    const fichier = await open(cheminJob, "r");
    const brut = await fichier.readFile("utf-8");
    await fichier.close();
    const actuel = JSON.parse(brut);
    if (actuel.statut === "termine" || actuel.statut === "erreur") return;
  } catch {
    // pas grave si le fichier est illisible/absent : on écrit l'erreur quand même
  }
  await writeFile(
    cheminJob,
    JSON.stringify(
      { statut: "erreur", etape: "inconnue", message: null, kpis: [], erreur: message },
      null,
      2
    )
  );
}

/**
 * Déclenche l'extraction des KPIs sur UN PDF précis, en arrière-plan.
 * Ne bloque pas : répond immédiatement avec un jobId, que le frontend suit
 * ensuite via /api/extraction-statut/[id].
 *
 * Fait appel à un script Python externe (extraire_un_pdf.py, côté backend)
 * qui n'existe pas forcément encore — dans ce cas cette route répond avec
 * une erreur claire plutôt que de rester bloquée sans réponse.
 *
 * Comme le reste de l'onglet Upload, ne fonctionne qu'en local (le script
 * Python tourne sur la machine, pas sur un déploiement Vercel).
 */
export async function POST(request: Request) {
  let corps: CorpsRequete;
  try {
    corps = (await request.json()) as CorpsRequete;
  } catch {
    return NextResponse.json({ ok: false, erreur: "Requête invalide." }, { status: 400 });
  }

  const { chemin, societe, annee } = corps;
  if (!chemin || typeof chemin !== "string") {
    return NextResponse.json({ ok: false, erreur: "Chemin du PDF manquant." }, { status: 400 });
  }
  if (!societe || typeof societe !== "string" || societe.trim().length < 2) {
    return NextResponse.json({ ok: false, erreur: "Nom de société manquant." }, { status: 400 });
  }
  if (!annee || typeof annee !== "number" || !Number.isInteger(annee)) {
    return NextResponse.json({ ok: false, erreur: "Année manquante ou invalide." }, { status: 400 });
  }

  const jobId = randomUUID();
  const cheminPdfAbsolu = path.join(RACINE_DEPOT, chemin);

  try {
    await mkdir(DOSSIER_JOBS, { recursive: true });
    await ecrireStatutInitial(jobId, societe.trim(), annee);

    const journal = await open(path.join(DOSSIER_JOBS, `${jobId}.log`), "a");
    const processus = spawn(
      PYTHON_BIN,
      [
        SCRIPT_EXTRACTION,
        "--pdf",
        cheminPdfAbsolu,
        "--societe",
        societe.trim(),
        "--annee",
        String(annee),
        "--job-id",
        jobId,
      ],
      {
        cwd: RACINE_DEPOT,
        detached: true,
        stdio: ["ignore", journal.fd, journal.fd],
      }
    );

    processus.on("error", (err) => {
      // ex. "python" introuvable sur le PATH — on le sait tout de suite
      marquerErreurSiPasDeja(
        jobId,
        `Impossible de démarrer le script d'extraction (${err.message}). Vérifiez que "${PYTHON_BIN}" est installé et accessible.`
      );
    });
    processus.on("exit", (code) => {
      journal.close();
      if (code !== 0) {
        marquerErreurSiPasDeja(
          jobId,
          `Le script d'extraction s'est arrêté de façon inattendue (code ${code}). Voir jobs/${jobId}.log pour le détail.`
        );
      }
    });
    processus.unref();

    return NextResponse.json({ ok: true, jobId });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { ok: false, erreur: `Échec du lancement de l'extraction : ${message}` },
      { status: 500 }
    );
  }
}
