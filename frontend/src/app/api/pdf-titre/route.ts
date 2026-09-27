import { NextResponse } from "next/server";
import { extraireTitrePage1, nettoyerNomFichier } from "@/lib/pdf-titre";

export const runtime = "nodejs";

/**
 * Étape 1 (dépôt de PDF) — appelée quand l'utilisateur choisit un fichier :
 * ne l'enregistre pas encore, propose juste un titre à confirmer/renommer.
 */
export async function POST(request: Request) {
  const forme = await request.formData();
  const fichier = forme.get("pdf");
  if (!(fichier instanceof File)) {
    return NextResponse.json({ erreur: "Aucun fichier PDF reçu." }, { status: 400 });
  }
  if (fichier.type && fichier.type !== "application/pdf" && !fichier.name.toLowerCase().endsWith(".pdf")) {
    return NextResponse.json({ erreur: "Le fichier doit être un PDF." }, { status: 400 });
  }

  const octets = new Uint8Array(await fichier.arrayBuffer());
  const titreExtrait = await extraireTitrePage1(octets);
  const nomNettoye = nettoyerNomFichier(fichier.name);

  return NextResponse.json({
    suggestion: titreExtrait ?? nomNettoye,
    titreExtrait,
    nomNettoye,
    tailleOctets: fichier.size,
  });
}
