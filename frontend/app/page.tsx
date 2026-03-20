/**
 * Main Page Component - IngredientIQ
 */
"use client";

import { useState } from "react";
import ProductSearch from "@/components/ProductSearch";
import IngredientAnalyzer from "@/components/IngredientAnalyzer";
import ImageUpload from "@/components/ImageUpload";
import ProductAnalysisResults from "@/components/ProductAnalysisResults";

export default function Home() {
  const [analysisResults, setAnalysisResults] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleError = (errorMsg: string) => {
    setError(errorMsg);
    setTimeout(() => setError(null), 5000);
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-cream to-sage-50">
      {/* Header */}
      <header className="bg-white border-b border-sage-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img
                src="/IngredientIQ_logo.png"
                alt="IngredientIQ Logo"
                className="w-20 h-20"
              />
              <div>
                <h1 className="text-4xl font-serif font-bold text-forest-800">
                  Ingredient<span className="text-terracotta-500">IQ</span>
                </h1>
                <p className="text-sage-600 text-sm mt-0.5 font-semibold">
                  Safety, Simplified
                </p>
              </div>
            </div>
            <div className="text-right text-sm text-sage-700">
              <p className="font-bold text-forest-700">Smart Analysis</p>
              <p className="text-xs text-sage-600">Powered by Claude AI</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-16">
        {/* Error Alert */}
        {error && (
          <div className="mb-8 p-4 bg-red-50 border border-red-300 rounded-lg text-red-700 text-sm flex items-start gap-3 animate-in fade-in">
            <span className="text-lg">⚠️</span>
            <div>{error}</div>
          </div>
        )}

        {/* Results Display */}
        {analysisResults ? (
          <div className="animate-in fade-in">
            <button
              onClick={() => {
                setAnalysisResults(null);
              }}
              className="mb-8 px-6 py-2.5 bg-forest-700 text-white rounded-lg hover:bg-forest-800 transition-all text-sm font-semibold hover:shadow-md active:scale-95"
            >
              ← New Analysis
            </button>
            <ProductAnalysisResults analysis={analysisResults} />
          </div>
        ) : (
          <>
            {/* Hero Section */}
            <div className="text-center mb-16">
              <h2 className="text-5xl font-serif font-bold text-forest-800 mb-4">
                Discover What's In Your Products
              </h2>
              <p className="text-xl text-sage-700 font-medium max-w-3xl mx-auto">
                Upload an image, search for a product, or enter ingredients to
                get AI-powered safety analysis with verified research backing
              </p>
            </div>

            {/* 3-Card Input Section */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
              {/* Card 1: Analyze Ingredients */}
              <div className="card card-hover">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-2xl font-serif font-bold text-forest-800">
                    📝 Analyze Ingredients
                  </h3>
                </div>
                <p className="text-sage-700 text-sm mb-6 font-medium">
                  Enter ingredient names directly to analyze their safety
                </p>
                <IngredientAnalyzer
                  onAnalysisComplete={setAnalysisResults}
                  onError={handleError}
                  cardLayout={true}
                />
              </div>

              {/* Card 2: Product Search */}
              <div className="card card-hover">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-2xl font-serif font-bold text-forest-800">
                    🔍 Product Search
                  </h3>
                </div>
                <p className="text-sage-700 text-sm mb-6 font-medium">
                  Search for a product by name and analyze its ingredients
                </p>
                <ProductSearch
                  onAnalysisComplete={setAnalysisResults}
                  onError={handleError}
                  cardLayout={true}
                />
              </div>

              {/* Card 3: Upload Image */}
              <div className="card card-hover">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-2xl font-serif font-bold text-forest-800">
                    📷 Upload Image
                  </h3>
                </div>
                <p className="text-sage-700 text-sm mb-6 font-medium">
                  Upload a product label for automatic text extraction
                </p>
                <ImageUpload
                  onAnalysisComplete={setAnalysisResults}
                  onError={handleError}
                  cardLayout={true}
                />
              </div>
            </div>

            {/* About IngredientIQ Section */}
            <div className="bg-white rounded-xl border border-sage-200 shadow-md p-12 mb-16">
              <h2 className="text-4xl font-serif font-bold text-forest-800 mb-12 text-center">
                About IngredientIQ
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
                {/* How It Works */}
                <div className="space-y-4">
                  <h3 className="text-2xl font-serif font-bold text-forest-700 flex items-center gap-3">
                    <span className="text-3xl">⚙️</span> How It Works
                  </h3>
                  <p className="text-sage-700 leading-relaxed font-medium">
                    Our AI system combines advanced language models with
                    verified chemical databases to analyze ingredients in
                    seconds.
                  </p>
                  <ul className="text-sm text-sage-600 space-y-2 font-medium">
                    <li className="flex items-start gap-2">
                      <span className="text-forest-700 mt-1">✓</span>
                      <span>Extract ingredients from images using OCR</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-forest-700 mt-1">✓</span>
                      <span>Search chemical safety databases</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-forest-700 mt-1">✓</span>
                      <span>Generate evidence-based recommendations</span>
                    </li>
                  </ul>
                </div>

                {/* Safety Ratings */}
                <div className="space-y-4">
                  <h3 className="text-2xl font-serif font-bold text-forest-700 flex items-center gap-3">
                    <span className="text-3xl">🛡️</span> Safety Ratings
                  </h3>
                  <p className="text-sage-700 leading-relaxed font-medium">
                    Each ingredient receives one of three safety classifications
                    based on scientific research and regulatory data.
                  </p>
                  <ul className="space-y-3 text-sm font-medium">
                    <li className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                      <span className="text-lg">✅</span>
                      <div>
                        <span className="font-bold text-green-700">SAFE</span>
                        <p className="text-green-600 text-xs">
                          No significant known risks
                        </p>
                      </div>
                    </li>
                    <li className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                      <span className="text-lg">⚠️</span>
                      <div>
                        <span className="font-bold text-yellow-700">
                          CAUTION
                        </span>
                        <p className="text-yellow-600 text-xs">
                          Potential risks at high doses
                        </p>
                      </div>
                    </li>
                    <li className="flex items-center gap-3 p-3 bg-red-50 rounded-lg border border-red-200">
                      <span className="text-lg">❌</span>
                      <div>
                        <span className="font-bold text-red-700">HARMFUL</span>
                        <p className="text-red-600 text-xs">
                          Known hazardous substance
                        </p>
                      </div>
                    </li>
                  </ul>
                </div>

                {/* Data Resources */}
                <div className="space-y-4">
                  <h3 className="text-2xl font-serif font-bold text-forest-700 flex items-center gap-3">
                    <span className="text-3xl">📚</span> Data Resources
                  </h3>
                  <p className="text-sage-700 leading-relaxed font-medium">
                    Our analysis is backed by authoritative sources trusted by
                    scientists and regulators worldwide.
                  </p>
                  <ul className="text-sm text-sage-600 space-y-2.5 font-medium">
                    <li className="flex items-center gap-2">
                      <span className="text-forest-700">•</span>
                      <span>
                        <strong>PubChem</strong> - NIH chemical database
                      </span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-forest-700">•</span>
                      <span>
                        <strong>FDA</strong> - Food & drug safety lists
                      </span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-forest-700">•</span>
                      <span>
                        <strong>EWG</strong> - Skin Deep hazard ratings
                      </span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-forest-700">•</span>
                      <span>
                        <strong>IARC</strong> - Carcinogen classifications
                      </span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-forest-700">•</span>
                      <span>
                        <strong>Open Food Facts</strong> - Product database
                      </span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <footer className="bg-forest-800 text-cream py-12 mt-20 border-t border-forest-900">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <p className="text-sm font-medium mb-2">
            IngredientIQ v1.0 — Making ingredient safety analysis accessible
          </p>
          <p className="text-xs text-sage-200">
            Evidence-based ingredient analysis powered by AI and verified
            research databases
          </p>
        </div>
      </footer>
    </main>
  );
}
