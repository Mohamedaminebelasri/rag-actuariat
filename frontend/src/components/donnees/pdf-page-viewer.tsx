"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { ChevronLeft, ChevronRight, Loader2, ZoomIn, ZoomOut } from "lucide-react";

type Mode = "single" | "scroll";

type Props = {
  /** URL du PDF (sans fragment #page) */
  url: string;
  /** Page à afficher au chargement */
  initialPage: number;
  /** Zoom initial (défaut : 1.75) */
  defaultZoom?: number;
  /** Callback quand le zoom change (pour persister le choix) */
  onZoomChange?: (zoom: number) => void;
  /** "single" (défaut, comportement historique — modal KPI) ou "scroll"
   * (défilement continu façon viewer Chrome — onglet Documents). */
  mode?: Mode;
};

/**
 * Viewer PDF basé sur pdfjs-dist. Point d'entrée : choisit entre le
 * rendu page-par-page historique (`mode="single"`, défaut — utilisé
 * par le modal KPI, jamais changé par ce refactoring) et le défilement
 * continu (`mode="scroll"`, onglet Documents uniquement).
 */
export function PdfPageViewer({ url, initialPage, defaultZoom = 1.75, onZoomChange, mode = "single" }: Props) {
  if (mode === "scroll") {
    return (
      <PdfScrollViewer url={url} initialPage={initialPage} defaultZoom={defaultZoom} onZoomChange={onZoomChange} />
    );
  }
  return <PdfSingleViewer url={url} initialPage={initialPage} defaultZoom={defaultZoom} onZoomChange={onZoomChange} />;
}

/* =======================================================================
   Mode "single" — implémentation historique, INCHANGÉE (le modal KPI
   n'a besoin de vérifier qu'1-2 pages, pas de défilement continu).
   ======================================================================= */

function PdfSingleViewer({
  url,
  initialPage,
  defaultZoom = 1.75,
  onZoomChange,
}: Omit<Props, "mode">) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pdfDocRef = useRef<any>(null);
  const renderTaskRef = useRef<{ cancel: () => void } | null>(null);

  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageInput, setPageInput] = useState(String(initialPage));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(defaultZoom);

  useEffect(() => { onZoomChange?.(zoom); }, [zoom, onZoomChange]);
  const [resizeKey, setResizeKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const pdfjsLib = await import("pdfjs-dist");
        pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

        // disableAutoFetch : pdfjs ne pré-télécharge PAS tout le fichier,
        // seulement les pages demandées (nécessite Accept-Ranges côté serveur).
        // rangeChunkSize : taille des morceaux téléchargés (64 Ko au lieu de
        // 65536 par défaut — identique ici mais explicite).
        // Résultat : pour un PDF de 621 pages (~20 Mo), le chargement initial
        // passe de ~5-10 s à < 1 s car seuls ~200 Ko sont téléchargés.
        const doc = await pdfjsLib.getDocument({
          url,
          disableAutoFetch: true,
          rangeChunkSize: 65536,
        }).promise;
        if (cancelled) return;

        pdfDocRef.current = doc;
        setTotalPages(doc.numPages);

        const clamped = Math.max(1, Math.min(initialPage, doc.numPages));
        setCurrentPage(clamped);
        setPageInput(String(clamped));
      } catch (err) {
        if (!cancelled) {
          console.error("PDF load error:", err);
          setError("Impossible de charger le PDF.");
        }
      }
    }

    load();
    return () => { cancelled = true; };
  }, [url, initialPage]);

  useEffect(() => {
    const doc = pdfDocRef.current;
    if (!doc || !canvasRef.current || !containerRef.current) return;

    let cancelled = false;

    async function render() {
      setLoading(true);

      if (renderTaskRef.current) {
        try { renderTaskRef.current.cancel(); } catch { /* ignore */ }
      }

      try {
        const page = await doc.getPage(currentPage);
        if (cancelled) return;

        const container = containerRef.current!;
        const canvas = canvasRef.current!;
        const ctx = canvas.getContext("2d")!;

        const cw = container.clientWidth;
        const ch = container.clientHeight;
        const vp0 = page.getViewport({ scale: 1 });
        const fitScale = Math.min((cw - 16) / vp0.width, (ch - 16) / vp0.height);
        const finalScale = fitScale * zoom;

        const dpr = window.devicePixelRatio || 1;
        const viewport = page.getViewport({ scale: finalScale * dpr });

        canvas.width = viewport.width;
        canvas.height = viewport.height;
        canvas.style.width = `${viewport.width / dpr}px`;
        canvas.style.height = `${viewport.height / dpr}px`;

        const task = page.render({ canvasContext: ctx, viewport });
        renderTaskRef.current = task;
        await task.promise;

        if (!cancelled) setLoading(false);
      } catch (err: unknown) {
        const name = (err as { name?: string })?.name;
        if (!cancelled && name !== "RenderingCancelled" && name !== "RenderingCancelledException") {
          console.error("PDF render error:", err);
          setError("Erreur lors du rendu de la page.");
          setLoading(false);
        }
      }
    }

    render();
    return () => { cancelled = true; };
  }, [currentPage, zoom, resizeKey, totalPages]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => {
      setResizeKey((k) => k + 1);
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const goToPage = useCallback(
    (p: number) => {
      const clamped = Math.max(1, Math.min(p, totalPages));
      setCurrentPage(clamped);
      setPageInput(String(clamped));
    },
    [totalPages]
  );

  const handlePageInputKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      const p = parseInt(pageInput, 10);
      if (!isNaN(p)) goToPage(p);
    }
  };

  const handlePageInputBlur = () => {
    const p = parseInt(pageInput, 10);
    if (!isNaN(p)) goToPage(p);
    else setPageInput(String(currentPage));
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-text-tertiary">
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-center gap-2 px-3 py-2 border-b border-border bg-surface-secondary/30 flex-shrink-0">
        <button
          onClick={() => goToPage(currentPage - 1)}
          disabled={currentPage <= 1}
          className="w-7 h-7 flex items-center justify-center rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-30 disabled:pointer-events-none"
          title="Page précédente"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-1.5 text-sm text-text-secondary">
          <span className="hidden sm:inline">Page</span>
          <input
            type="text"
            inputMode="numeric"
            value={pageInput}
            onChange={(e) => setPageInput(e.target.value)}
            onKeyDown={handlePageInputKey}
            onBlur={handlePageInputBlur}
            className="w-12 text-center rounded-md border border-border bg-surface px-1 py-0.5 text-sm text-text-primary font-mono focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <span>/ {totalPages || "…"}</span>
        </div>

        <button
          onClick={() => goToPage(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="w-7 h-7 flex items-center justify-center rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-30 disabled:pointer-events-none"
          title="Page suivante"
        >
          <ChevronRight className="w-4 h-4" />
        </button>

        <div className="w-px h-5 bg-border mx-1 hidden sm:block" />

        <button
          onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
          disabled={zoom <= 0.5}
          className="w-7 h-7 flex items-center justify-center rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-30 disabled:pointer-events-none hidden sm:flex"
          title="Zoom arrière"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <span className="text-xs text-text-tertiary font-mono w-10 text-center hidden sm:inline">
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
          disabled={zoom >= 3}
          className="w-7 h-7 flex items-center justify-center rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-30 disabled:pointer-events-none hidden sm:flex"
          title="Zoom avant"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
      </div>

      <div
        ref={containerRef}
        className="relative flex-1 min-h-0 overflow-auto flex justify-center items-start bg-neutral-100 dark:bg-neutral-900"
      >
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
            <Loader2 className="w-8 h-8 text-accent animate-spin" />
          </div>
        )}
        <canvas ref={canvasRef} className="block my-2 shadow-lg" />
      </div>
    </div>
  );
}

/* =======================================================================
   Mode "scroll" — défilement continu (onglet Documents uniquement).

   Principe : toutes les pages sont des "slots" empilés verticalement,
   chacun pré-dimensionné (hauteur/largeur connues dès le chargement des
   métadonnées, avant tout rendu) pour que la scrollbar ait la bonne
   taille dès le départ. Seules les pages dans la FENÊTRE TAMPON (page
   visible ± BUFFER_PAGES) portent un <canvas> réellement rendu ; les
   autres sont un simple <div> vide de la bonne taille (placeholder) —
   sans quoi un PDF de 600+ pages (Aéma) créerait 600+ canvas en mémoire
   simultanément. Un IntersectionObserver par slot met à jour la page
   courante (indicateur) et la fenêtre tampon au fil du scroll.
   ======================================================================= */

const BUFFER_PAGES = 3; // pages rendues avant/après la page visible

type Viewport1x = { width: number; height: number };

function PdfScrollViewer({ url, initialPage, defaultZoom = 1.75, onZoomChange }: Omit<Props, "mode">) {
  const containerRef = useRef<HTMLDivElement>(null);
  const slotRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const canvasRefs = useRef<Map<number, HTMLCanvasElement>>(new Map());
  const renderTasksRef = useRef<Map<number, { cancel: () => void }>>(new Map());
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pdfDocRef = useRef<any>(null);
  const initialScrollDone = useRef(false);

  const [viewports, setViewports] = useState<Viewport1x[] | null>(null); // index 0 = page 1
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageInput, setPageInput] = useState(String(initialPage));
  const [zoom, setZoom] = useState(defaultZoom);
  const [error, setError] = useState<string | null>(null);
  const [visibleRange, setVisibleRangeRaw] = useState<{ start: number; end: number }>({
    start: initialPage,
    end: initialPage,
  });
  // BUG RÉEL trouvé en test (navigateur gelé) : appeler setVisibleRange
  // avec un NOUVEL OBJET à chaque callback de l'IntersectionObserver -
  // même quand start/end sont identiques - fait re-render l'effet de
  // rendu (dépendance [visibleRange, layout]) en boucle, qui annule et
  // relance les rendus canvas sans fin, jusqu'à geler l'onglet. Ne
  // déclenche une mise à jour que si les valeurs changent réellement.
  const setVisibleRange = useCallback((next: { start: number; end: number }) => {
    setVisibleRangeRaw((prev) => (prev.start === next.start && prev.end === next.end ? prev : next));
  }, []);
  const [fitWidth, setFitWidth] = useState(800);

  useEffect(() => { onZoomChange?.(zoom); }, [zoom, onZoomChange]);

  /* ── Charger le PDF + les dimensions de TOUTES les pages (métadonnée
     seule, pas un rendu canvas — reste rapide même sur 600+ pages) ── */
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const pdfjsLib = await import("pdfjs-dist");
        pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

        const doc = await pdfjsLib.getDocument({
          url,
          disableAutoFetch: true,
          rangeChunkSize: 65536,
        }).promise;
        if (cancelled) return;
        pdfDocRef.current = doc;

        const vps: Viewport1x[] = [];
        for (let i = 1; i <= doc.numPages; i++) {
          const page = await doc.getPage(i);
          if (cancelled) return;
          const vp = page.getViewport({ scale: 1 });
          vps.push({ width: vp.width, height: vp.height });
        }
        if (!cancelled) setViewports(vps);
      } catch (err) {
        if (!cancelled) {
          console.error("PDF load error:", err);
          setError("Impossible de charger le PDF.");
        }
      }
    }

    load();
    return () => { cancelled = true; };
  }, [url]);

  /* ── Largeur de référence (fit-to-width du conteneur) ────────────── */
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(() => {
      setFitWidth(container.clientWidth - 32);
    });
    observer.observe(container);
    setFitWidth(container.clientWidth - 32);
    return () => observer.disconnect();
  }, []);

  /* ── Échelle effective par page (fit-largeur × zoom), et disposition
     cumulée (offset vertical de chaque page) ─────────────────────── */
  const layout = useMemo(() => {
    if (!viewports || viewports.length === 0 || fitWidth <= 0) return null;
    const baseScale = fitWidth / viewports[0].width; // toutes les pages QRT ont la même largeur en pratique
    const scale = baseScale * zoom;
    let offset = 0;
    const pages = viewports.map((vp) => {
      const width = vp.width * scale;
      const height = vp.height * scale;
      const top = offset;
      offset += height + PAGE_GAP;
      return { width, height, top, scale };
    });
    return { pages, totalHeight: offset, scale };
  }, [viewports, fitWidth, zoom]);

  /* ── Scroll initial vers initialPage, une seule fois quand la
     disposition est connue ──────────────────────────────────────── */
  useEffect(() => {
    if (initialScrollDone.current || !layout || !containerRef.current) return;
    const cible = Math.max(1, Math.min(initialPage, layout.pages.length));
    const idx = cible - 1;
    containerRef.current.scrollTop = layout.pages[idx].top;
    // Même raison que goToPage : ne pas compter uniquement sur
    // l'IntersectionObserver pour la fenêtre tampon après un saut loin
    // de la page 1 (ex. lien KPI vers la page 547 d'un document de 621
    // pages) — fixé directement ici.
    setCurrentPage(cible);
    setPageInput(String(cible));
    setVisibleRange({
      start: Math.max(1, cible - BUFFER_PAGES),
      end: Math.min(layout.pages.length, cible + BUFFER_PAGES),
    });
    initialScrollDone.current = true;
  }, [layout, initialPage, setVisibleRange]);

  /* ── Zoom : garder la position relative de scroll (mise à l'échelle
     uniforme -> le ratio scrollTop/totalHeight reste exact) ──────── */
  const prevTotalHeight = useRef<number | null>(null);
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !layout) return;
    if (prevTotalHeight.current && prevTotalHeight.current > 0) {
      const ratio = container.scrollTop / prevTotalHeight.current;
      container.scrollTop = ratio * layout.totalHeight;
    }
    prevTotalHeight.current = layout.totalHeight;
    // volontairement pas de dépendance sur layout entier : ne réagir
    // qu'aux changements de zoom, pas au premier calcul de layout
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoom]);

  /* ── IntersectionObserver : page courante + fenêtre tampon ───────── */
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !layout) return;

    const ratios = new Map<number, number>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const page = Number((entry.target as HTMLElement).dataset.page);
          ratios.set(page, entry.isIntersecting ? entry.intersectionRatio : 0);
        }
        let meilleur = currentPage;
        let meilleurRatio = -1;
        for (const [page, ratio] of ratios) {
          if (ratio > meilleurRatio) {
            meilleurRatio = ratio;
            meilleur = page;
          }
        }
        if (meilleurRatio > 0) {
          setCurrentPage(meilleur);
          setPageInput(String(meilleur));
          setVisibleRange({
            start: Math.max(1, meilleur - BUFFER_PAGES),
            end: Math.min(layout.pages.length, meilleur + BUFFER_PAGES),
          });
        }
      },
      { root: container, threshold: [0, 0.1, 0.5, 1] }
    );

    for (const el of slotRefs.current.values()) observer.observe(el);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout]);

  /* ── Rendu des canvas dans la fenêtre tampon, libération hors fenêtre ──
     Rendus en PARALLÈLE (pas une boucle séquentielle avec await) : une
     boucle séquentielle laissait une page lente (ex. un saut lointain,
     page 2 -> 80) bloquer indéfiniment les pages suivantes de la même
     fenêtre — constaté en test réel (page 77 se met à jour, 78-83 jamais
     rendues). Chaque page a sa propre tâche annulée explicitement au
     nettoyage de CET effet précisément (pas seulement un flag lu entre
     itérations d'une boucle qui, elle, ne l'était jamais si bloquée sur
     un await). */
  useEffect(() => {
    const doc = pdfDocRef.current;
    if (!doc || !layout) return;
    const layoutActuel = layout;

    let cancelled = false;
    const tachesDeCetEffet: { cancel: () => void }[] = [];

    async function renderPage(n: number) {
      const canvas = canvasRefs.current.get(n);
      if (!canvas || cancelled) return;
      if (canvas.dataset.renderedScale === String(layoutActuel.scale)) return;

      const ancienne = renderTasksRef.current.get(n);
      if (ancienne) { try { ancienne.cancel(); } catch { /* ignore */ } }

      try {
        const page = await doc.getPage(n);
        if (cancelled) return;
        const ctx = canvas.getContext("2d")!;
        const dpr = window.devicePixelRatio || 1;
        const viewport = page.getViewport({ scale: layoutActuel.scale * dpr });
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        canvas.style.width = `${viewport.width / dpr}px`;
        canvas.style.height = `${viewport.height / dpr}px`;
        const task = page.render({ canvasContext: ctx, viewport });
        renderTasksRef.current.set(n, task);
        tachesDeCetEffet.push(task);
        await task.promise;
        if (!cancelled) canvas.dataset.renderedScale = String(layoutActuel.scale);
      } catch (err: unknown) {
        const name = (err as { name?: string })?.name;
        if (name !== "RenderingCancelled" && name !== "RenderingCancelledException") {
          console.error(`PDF render error (page ${n}):`, err);
        }
      }
    }

    const pages: number[] = [];
    for (let n = visibleRange.start; n <= visibleRange.end; n++) pages.push(n);
    Promise.all(pages.map(renderPage));

    return () => {
      cancelled = true;
      for (const t of tachesDeCetEffet) { try { t.cancel(); } catch { /* ignore */ } }
    };
  }, [visibleRange, layout]);

  const goToPage = useCallback(
    (p: number) => {
      if (!layout) return;
      const cible = Math.max(1, Math.min(p, layout.pages.length));
      const idx = cible - 1;
      // "instant", pas "smooth" : un saut lointain (ex. page 2 -> 80) anime
      // le scroll sur des dizaines de slots, chacun déclenchant
      // l'IntersectionObserver à chaque frame -> tempête de recalculs de
      // fenêtre tampon + rendus canvas annulés/relancés en boucle, au point
      // de geler l'onglet (constaté en test réel). Un saut instantané ne
      // déclenche l'observer qu'une fois, à l'arrivée.
      containerRef.current?.scrollTo({ top: layout.pages[idx].top, behavior: "auto" });
      // Ne PAS dépendre uniquement de l'IntersectionObserver pour la
      // fenêtre tampon après un saut instantané loin de la position
      // actuelle : constaté en test réel qu'il ne se redéclenche pas de
      // façon fiable dans ce cas précis (0 callback reçu même après
      // plusieurs secondes, alors que la géométrie était correcte) —
      // fixé directement ici, l'observer prend ensuite le relais pour le
      // scroll naturel de l'utilisateur.
      setCurrentPage(cible);
      setPageInput(String(cible));
      setVisibleRange({
        start: Math.max(1, cible - BUFFER_PAGES),
        end: Math.min(layout.pages.length, cible + BUFFER_PAGES),
      });
    },
    [layout, setVisibleRange]
  );

  const handlePageInputKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      const p = parseInt(pageInput, 10);
      if (!isNaN(p)) goToPage(p);
    }
  };
  const handlePageInputBlur = () => {
    const p = parseInt(pageInput, 10);
    if (!isNaN(p)) goToPage(p);
    else setPageInput(String(currentPage));
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-text-tertiary">
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-center gap-2 px-3 py-2 border-b border-border bg-surface-secondary/30 flex-shrink-0">
        <button
          onClick={() => goToPage(currentPage - 1)}
          disabled={currentPage <= 1}
          className="w-7 h-7 flex items-center justify-center rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-30 disabled:pointer-events-none"
          title="Page précédente"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-1.5 text-sm text-text-secondary">
          <span className="hidden sm:inline">Page</span>
          <input
            type="text"
            inputMode="numeric"
            value={pageInput}
            onChange={(e) => setPageInput(e.target.value)}
            onKeyDown={handlePageInputKey}
            onBlur={handlePageInputBlur}
            className="w-12 text-center rounded-md border border-border bg-surface px-1 py-0.5 text-sm text-text-primary font-mono focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <span>/ {layout?.pages.length ?? "…"}</span>
        </div>

        <button
          onClick={() => goToPage(currentPage + 1)}
          disabled={!layout || currentPage >= layout.pages.length}
          className="w-7 h-7 flex items-center justify-center rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-30 disabled:pointer-events-none"
          title="Page suivante"
        >
          <ChevronRight className="w-4 h-4" />
        </button>

        <div className="w-px h-5 bg-border mx-1 hidden sm:block" />

        <button
          onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
          disabled={zoom <= 0.5}
          className="w-7 h-7 flex items-center justify-center rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-30 disabled:pointer-events-none hidden sm:flex"
          title="Zoom arrière"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <input
          type="range"
          min={50}
          max={300}
          step={25}
          value={Math.round(zoom * 100)}
          onChange={(e) => setZoom(Number(e.target.value) / 100)}
          className="hidden sm:block w-20 accent-[var(--color-accent)]"
          title="Zoom"
        />
        <span className="text-xs text-text-tertiary font-mono w-10 text-center hidden sm:inline">
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
          disabled={zoom >= 3}
          className="w-7 h-7 flex items-center justify-center rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-30 disabled:pointer-events-none hidden sm:flex"
          title="Zoom avant"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
      </div>

      <div
        ref={containerRef}
        className="relative flex-1 min-h-0 overflow-auto flex flex-col items-center bg-neutral-100 dark:bg-neutral-900"
      >
        {!layout && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <Loader2 className="w-8 h-8 text-accent animate-spin" />
          </div>
        )}
        {layout && (
          <div style={{ position: "relative", height: layout.totalHeight, width: "100%" }}>
            {layout.pages.map((p, i) => {
              const n = i + 1;
              const dansTampon = n >= visibleRange.start && n <= visibleRange.end;
              return (
                <div
                  key={n}
                  data-page={n}
                  ref={(el) => {
                    if (el) slotRefs.current.set(n, el);
                    else slotRefs.current.delete(n);
                  }}
                  style={{
                    position: "absolute",
                    top: p.top,
                    left: "50%",
                    transform: "translateX(-50%)",
                    width: p.width,
                    height: p.height,
                  }}
                  className="shadow-lg bg-white"
                >
                  {dansTampon ? (
                    <canvas
                      ref={(el) => {
                        if (el) canvasRefs.current.set(n, el);
                        else canvasRefs.current.delete(n);
                      }}
                      style={{ width: p.width, height: p.height, display: "block" }}
                    />
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

const PAGE_GAP = 12; // espace vertical entre pages, en px
