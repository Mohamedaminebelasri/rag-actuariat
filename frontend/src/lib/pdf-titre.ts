/**
 * pdf-titre.ts — Suggestion de titre pour un PDF déposé dans l'onglet
 * "Ajouter un PDF" (étape 1 du circuit d'ingestion : dépôt + confirmation
 * du nom, avant l'extraction des KPIs qui reste une étape séparée, à
 * faire plus tard).
 *
 * Usage strictement serveur (route API Next.js, runtime Node) : pdfjs-dist
 * "legacy" est fait pour tourner sans worker/DOM. Ne pas importer ce
 * module depuis un composant client.
 */
import "server-only";

type ItemTexte = { str: string; x: number; y: number; taillePolice: number };

/** Certains PDF (police mal déclarée, table ToUnicode absente ou erronée —
 * on l'a vu avec des générateurs comme wkhtmltopdf) font ressortir du texte
 * UTF-8 ré-encodé en Latin-1 par erreur ("SolvabilitÃ©" au lieu de
 * "Solvabilité"). On répare seulement quand la signature de ce bug est
 * détectée et que le résultat après réparation en a manifestement moins —
 * jamais sur du texte qui n'a pas ce défaut. */
function repererEtReparerEncodage(texte: string): string {
  const motifMojibake = /[ÃÂ][\u0080-¿]/g;
  if (!motifMojibake.test(texte)) return texte;
  try {
    const reparee = Buffer.from(texte, "latin1").toString("utf8");
    if (reparee.includes("�")) return texte;
    const avant = (texte.match(motifMojibake) ?? []).length;
    const apres = (reparee.match(motifMojibake) ?? []).length;
    return apres < avant ? reparee : texte;
  } catch {
    return texte;
  }
}

/** Regroupe les items de texte d'une page en lignes (même ordonnée à
 * epsilon près), triées de haut en bas puis de gauche à droite. */
function regrouperEnLignes(items: ItemTexte[]): { y: number; taillePolice: number; texte: string }[] {
  const EPSILON_Y = 2;
  const tries = [...items].sort((a, b) => b.y - a.y || a.x - b.x);
  const lignes: { y: number; taillePolice: number; texte: string }[] = [];

  for (const item of tries) {
    const ligne = lignes.find((l) => Math.abs(l.y - item.y) <= EPSILON_Y);
    if (ligne) {
      ligne.texte += item.str;
      ligne.taillePolice = Math.max(ligne.taillePolice, item.taillePolice);
    } else {
      lignes.push({ y: item.y, taillePolice: item.taillePolice, texte: item.str });
    }
  }
  return lignes;
}

/** Tente de deviner le "grand titre" de la page 1 d'un PDF : la ligne à
 * la police la plus grande, dans le premier tiers de la page, qui
 * ressemble à un titre (ni trop courte, ni trop longue, pas que des
 * chiffres). Retourne null si la page n'a pas de couche de texte
 * exploitable (PDF scanné en image, par ex.) ou si rien ne ressort. */
export async function extraireTitrePage1(bytes: Uint8Array): Promise<string | null> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const pdfjs: any = await import("pdfjs-dist/legacy/build/pdf.mjs");
    const doc = await pdfjs.getDocument({
      data: bytes,
      useWorkerFetch: false,
      isEvalSupported: false,
      disableFontFace: true,
    }).promise;

    const page = await doc.getPage(1);
    const viewport = page.getViewport({ scale: 1 });
    const contenu = await page.getTextContent();

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const items: ItemTexte[] = (contenu.items as any[])
      .filter((it) => typeof it.str === "string" && it.str.trim().length > 0)
      .map((it) => ({
        str: repererEtReparerEncodage(it.str as string),
        x: it.transform[4] as number,
        y: it.transform[5] as number,
        taillePolice: Math.hypot(it.transform[2], it.transform[3]),
      }));

    await doc.destroy();
    if (items.length === 0) return null;

    const lignes = regrouperEnLignes(items)
      // premier tiers de la page (haut) : le grand titre y est presque toujours
      .filter((l) => l.y > viewport.height * 0.6)
      .map((l) => ({ ...l, texte: l.texte.replace(/\s+/g, " ").trim() }))
      .filter((l) => {
        const t = l.texte;
        if (t.length < 6 || t.length > 140) return false;
        if (/^[\d\s./-]+$/.test(t)) return false; // dates, numéros de page seuls
        return true;
      });
    if (lignes.length === 0) return null;

    const tailleMax = Math.max(...lignes.map((l) => l.taillePolice));
    // Concatène les lignes qui partagent (à peu près) la plus grande police,
    // consécutives : un titre tient parfois sur 2 lignes.
    const candidates = lignes.filter((l) => l.taillePolice >= tailleMax - 0.5);
    const titre = candidates
      .map((l) => l.texte)
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();

    return titre.length >= 6 ? titre : null;
  } catch {
    // PDF illisible par pdfjs, image scannée sans couche texte, etc. —
    // ce n'est pas bloquant, l'utilisateur garde le nom de fichier nettoyé.
    return null;
  }
}

/** Repli fiable quand la page 1 n'a pas donné de bon candidat : le nom de
 * fichier d'origine, juste nettoyé des séparateurs techniques. Ne touche
 * pas à la casse (pour ne pas abîmer des sigles comme SFCR, QRT, IARD). */
export function nettoyerNomFichier(nomOriginal: string): string {
  return nomOriginal
    .replace(/\.pdf$/i, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Transforme un titre confirmé par l'utilisateur en nom de fichier sûr
 * (Windows + Unix), sans le rendre méconnaissable. */
export function nomFichierSur(titre: string): string {
  const base = titre
    .trim()
    .replace(/[\\/:*?"<>|]/g, "-")
    .replace(/\s+/g, " ")
    .slice(0, 150)
    .trim();
  return `${base || "document"}.pdf`;
}
