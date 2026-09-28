import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // pdfjs-dist (extraction du titre PDF, onglet Upload) a du code natif
  // Node (canvas en dépendance optionnelle) : le laisser en require()
  // natif côté serveur évite les erreurs de bundling webpack.
  serverExternalPackages: ["pdfjs-dist"],

  webpack: (config, { isServer }) => {
    if (!isServer) {
      // pdfjs-dist côté client n'a pas besoin du module canvas Node.js
      config.resolve = config.resolve || {};
      config.resolve.alias = config.resolve.alias || {};

      config.resolve.alias.canvas = false;
    }
    return config;
  },
};

export default nextConfig;
