import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IngredientIQ - AI Ingredient Safety Analysis",
  description:
    "Analyze product ingredients for safety using AI-powered RAG research",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
