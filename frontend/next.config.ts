import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // pdfjs-dist (extraction du titre PDF, onglet Upload) a du code natif
  // Node (canvas en dépendance optionnelle) : le laisser en require()
  // natif côté serveur évite les erreurs de bundling webpack.
  serverExternalPackages: ["pdfjs-dist"],
};

export default nextConfig;
