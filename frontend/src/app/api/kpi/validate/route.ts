import { NextResponse } from "next/server";

export const runtime = "nodejs";

const VALIDATIONS_BLOB_KEY = "kpi-validations/validations.json";

type ValidationHumaine = {
  par: string;
  date: string;
};
type ValidationsMap = Record<string, ValidationHumaine>; // clé = "societe::kpiId"

async function lireValidationsBlob(): Promise<ValidationsMap> {
  const { get } = await import("@vercel/blob");
  try {
    const result = await get(VALIDATIONS_BLOB_KEY, { access: "private" });
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
    return JSON.parse(texte) as ValidationsMap;
  } catch {
    return {};
  }
}

async function ecrireValidationsBlob(validations: ValidationsMap): Promise<void> {
  const { put } = await import("@vercel/blob");
  const contenu = JSON.stringify(validations, null, 2);
  await put(VALIDATIONS_BLOB_KEY, contenu, {
    access: "private",
    contentType: "application/json",
    addRandomSuffix: false,
    allowOverwrite: true,
  });
}

// GET — Toutes les validations humaines
export async function GET() {
  if (!process.env.VERCEL) {
    return NextResponse.json({ validations: {} });
  }
  try {
    const validations = await lireValidationsBlob();
    return NextResponse.json({ validations });
  } catch (err) {
    return NextResponse.json(
      { validations: {}, erreur: err instanceof Error ? err.message : String(err) },
      { status: 500 }
    );
  }
}

// POST — Marquer un KPI comme traité par un humain
type CorpsRequete = {
  societe?: string;
  kpiId?: string;
  par?: string;
};

export async function POST(request: Request) {
  let corps: CorpsRequete;
  try {
    corps = (await request.json()) as CorpsRequete;
  } catch {
    return NextResponse.json({ ok: false, erreur: "Requête invalide." }, { status: 400 });
  }

  const { societe, kpiId, par } = corps;
  if (!societe || typeof societe !== "string" || !societe.trim()) {
    return NextResponse.json({ ok: false, erreur: "Société manquante." }, { status: 400 });
  }
  if (!kpiId || typeof kpiId !== "string" || !kpiId.trim()) {
    return NextResponse.json({ ok: false, erreur: "kpiId manquant." }, { status: 400 });
  }

  if (!process.env.VERCEL) {
    return NextResponse.json({ ok: false, erreur: "Non disponible en local." }, { status: 501 });
  }

  try {
    const validations = await lireValidationsBlob();
    const cle = `${societe.trim()}::${kpiId.trim()}`;
    validations[cle] = {
      par: (par && typeof par === "string" && par.trim()) || "Analyste",
      date: new Date().toISOString(),
    };
    await ecrireValidationsBlob(validations);
    return NextResponse.json({ ok: true });
  } catch (err) {
    return NextResponse.json(
      { ok: false, erreur: err instanceof Error ? err.message : String(err) },
      { status: 500 }
    );
  }
}

// DELETE — Retirer une validation (ou toutes)
export async function DELETE(request: Request) {
  if (!process.env.VERCEL) {
    return NextResponse.json({ ok: false, erreur: "Non disponible en local." }, { status: 501 });
  }

  try {
    const url = new URL(request.url);
    const cle = url.searchParams.get("cle");

    if (cle) {
      const validations = await lireValidationsBlob();
      if (!(cle in validations)) {
        return NextResponse.json({ ok: false, erreur: `Clé "${cle}" introuvable.` }, { status: 404 });
      }
      delete validations[cle];
      await ecrireValidationsBlob(validations);
      return NextResponse.json({ ok: true, supprimee: cle });
    }

    await ecrireValidationsBlob({});
    return NextResponse.json({ ok: true, message: "Toutes les validations ont été supprimées." });
  } catch (err) {
    return NextResponse.json(
      { ok: false, erreur: err instanceof Error ? err.message : String(err) },
      { status: 500 }
    );
  }
}
