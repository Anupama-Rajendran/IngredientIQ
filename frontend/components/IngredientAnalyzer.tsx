/**
 * Ingredient Analyzer Component
 */
"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface IngredientAnalyzerProps {
  onAnalysisComplete: (results: any) => void;
  onError: (error: string) => void;
  cardLayout?: boolean;
}

export default function IngredientAnalyzer({
  onAnalysisComplete,
  onError,
  cardLayout = false,
}: IngredientAnalyzerProps) {
  const [ingredientInput, setIngredientInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ingredientInput.trim()) {
      onError("Please enter at least one ingredient");
      return;
    }

    // Parse ingredients (comma-separated)
    const ingredients = ingredientInput
      .split(",")
      .map((ing) => ing.trim())
      .filter((ing) => ing.length > 0);

    if (ingredients.length === 0) {
      onError("Please enter valid ingredients");
      return;
    }

    setIsLoading(true);
    try {
      const results = await api.analyzeIngredients(ingredients);
      onAnalysisComplete(results);
    } catch (error) {
      onError(`Failed to analyze ingredients: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  if (cardLayout) {
    return (
      <form onSubmit={handleAnalyze} className="w-full space-y-4">
        <textarea
          value={ingredientInput}
          onChange={(e) => setIngredientInput(e.target.value)}
          placeholder="Enter ingredients separated by commas"
          className="w-full px-4 py-2.5 border border-sage-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-700 focus:border-forest-700 resize-none text-sm font-medium"
          rows={3}
        />
        <button
          type="submit"
          disabled={isLoading || !ingredientInput.trim()}
          className="btn-primary w-full"
        >
          {isLoading ? "🔄 Analyzing..." : "✓ Analyze"}
        </button>
        <p className="text-sage-600 text-xs font-medium">
          Separate with commas (e.g., "water, glycerin, sodium lauryl sulfate")
        </p>
      </form>
    );
  }

  return (
    <form onSubmit={handleAnalyze} className="w-full">
      <div className="space-y-4">
        <textarea
          value={ingredientInput}
          onChange={(e) => setIngredientInput(e.target.value)}
          placeholder="Enter ingredients separated by commas (e.g., water, glycerin, titanium dioxide)"
          className="w-full p-3 border border-sage-300 rounded-lg focus:ring-2 focus:ring-forest-700 focus:border-transparent resize-none text-sm font-medium"
          rows={4}
        />
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={isLoading}
            className="flex-1 btn-primary"
          >
            {isLoading ? "Analyzing..." : "Analyze Ingredients"}
          </button>
        </div>
        <p className="text-sm text-sage-600 leading-relaxed font-medium">
          Separate ingredients with commas. Example: "sodium lauryl sulfate,
          parabens, fragrance"
        </p>
      </div>
    </form>
  );
}
