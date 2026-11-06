import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AstraFlame // Microgravity Combustion Visualizer & Risk Matrix",
  description:
    "Agnishikha - NASA Space Apps Mission Control dashboard for microgravity flammability telemetry, flame visualization, AI SHAP explainability and fire mitigation protocols.",
  keywords: [
    "NASA Space Apps",
    "microgravity combustion",
    "flammability",
    "fire safety",
    "ISS",
    "PSI",
    "risk matrix",
    "SHAP explainability",
    "AstraFlame",
    "Agnishikha",
  ],
  authors: [{ name: "Agnishikha // AstraFlame" }],
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#020617",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 font-sans text-slate-100 antialiased selection:bg-orange-500/30 selection:text-orange-50">
        {children}
      </body>
    </html>
  );
}
