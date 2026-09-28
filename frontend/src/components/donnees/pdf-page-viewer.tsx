"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { ChevronLeft, ChevronRight, Loader2, ZoomIn, ZoomOut } from "lucide-react";

type Props = {
  /** URL du PDF (sans fragment #page) */
  url: string;
  /** Page à afficher au chargement */
  initialPage: number;
  /** Zoom initial (défaut : 1.75) */
  defaultZoom?: number;
  /** Callback quand le zoom change (pour persister le choix) */
  onZoomChange?: (zoom: number) => void;
};

/**
 * Viewer PDF basé sur pdfjs-dist avec navigation par page.
 * Fonctionne sur tous les navigateurs y compris iOS Safari,
 * contrairement à l'approche iframe + #page=N.
 */
export function PdfPageViewer({ url, initialPage, defaultZoom = 1.75, onZoomChange }: Props) {
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

  // Notifier le parent quand le zoom change
  useEffect(() => { onZoomChange?.(zoom); }, [zoom, onZoomChange]);
  const [resizeKey, setResizeKey] = useState(0);

  /* ── Charger le PDF ─────────────────────────────────────── */
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const pdfjsLib = await import("pdfjs-dist");
        pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

        const doc = await pdfjsLib.getDocument(url).promise;
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

  /* ── Rendre la page courante ────────────────────────────── */
  useEffect(() => {
    const doc = pdfDocRef.current;
    if (!doc || !canvasRef.current || !containerRef.current) return;

    let cancelled = false;

    async function render() {
      setLoading(true);

      // Remonter le conteneur en haut pour la nouvelle page
      if (containerRef.current) containerRef.current.scrollTop = 0;

      // Annuler le rendu précédent
      if (renderTaskRef.current) {
        try { renderTaskRef.current.cancel(); } catch { /* ignore */ }
      }

      try {
        const page = await doc.getPage(currentPage);
        if (cancelled) return;

        const container = containerRef.current!;
        const canvas = canvasRef.current!;
        const ctx = canvas.getContext("2d")!;

        // Calculer l'échelle pour remplir la largeur du conteneur
        const cw = container.clientWidth;
        const ch = container.clientHeight;
        const vp0 = page.getViewport({ scale: 1 });
        const fitScale = Math.min((cw - 16) / vp0.width, (ch - 16) / vp0.height);
        const finalScale = fitScale * zoom;

        // Haute résolution (retina)
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

  /* ── Re-rendre quand le conteneur est redimensionné ─────── */
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => {
      // Forcer un re-render en changeant zoom de façon invisible
      setResizeKey((k) => k + 1);
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  /* ── Navigation par molette (scroll) entre pages ────────── */
  useEffect(() => {
    const container = containerRef.current;
    if (!container || totalPages <= 1) return;

    let cooldown = false;

    const handleWheel = (e: WheelEvent) => {
      if (cooldown) return;

      const { scrollTop, scrollHeight, clientHeight } = container;
      const atBottom = scrollTop + clientHeight >= scrollHeight - 2;
      const atTop = scrollTop <= 2;

      if (e.deltaY > 0 && atBottom) {
        // Scroll vers le bas + déjà en bas → page suivante
        e.preventDefault();
        setCurrentPage((p) => {
          if (p >= totalPages) return p;
          const next = p + 1;
          setPageInput(String(next));
          return next;
        });
        cooldown = true;
        setTimeout(() => { cooldown = false; }, 400);
      } else if (e.deltaY < 0 && atTop) {
        // Scroll vers le haut + déjà en haut → page précédente
        e.preventDefault();
        setCurrentPage((p) => {
          if (p <= 1) return p;
          const prev = p - 1;
          setPageInput(String(prev));
          return prev;
        });
        cooldown = true;
        setTimeout(() => { cooldown = false; }, 400);
      }
    };

    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => container.removeEventListener("wheel", handleWheel);
  }, [totalPages]);

  /* ── Navigation ─────────────────────────────────────────── */
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

  /* ── Rendu ──────────────────────────────────────────────── */
  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-text-tertiary">
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Barre de navigation */}
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

      {/* Zone de rendu PDF */}
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
