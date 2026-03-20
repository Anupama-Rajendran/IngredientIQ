/**
 * Product Search Component
 */
"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface ProductSearchProps {
  onAnalysisComplete: (results: any) => void;
  onError: (error: string) => void;
  cardLayout?: boolean;
}

export default function ProductSearch({
  onAnalysisComplete,
  onError,
  cardLayout = false,
}: ProductSearchProps) {
  const [productName, setProductName] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productName.trim()) {
      onError("Please enter a product name");
      return;
    }

    setIsLoading(true);
    try {
      console.log("Searching for product:", productName);
      const results = await api.analyzeProduct(productName.trim());
      console.log("Product analysis results:", results);
      onAnalysisComplete(results);
    } catch (error: any) {
      const errorMsg = error?.message || String(error);
      console.warn("Product search failed:", errorMsg);
      onError(`Product not found: ${productName}`);
    } finally {
      setIsLoading(false);
    }
  };

  if (cardLayout) {
    return (
      <form onSubmit={handleSearch} className="w-full space-y-4">
        <input
          type="text"
          value={productName}
          onChange={(e) => setProductName(e.target.value)}
          placeholder="e.g., 'Neutrogena Sunscreen'"
          className="input-field w-full"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !productName.trim()}
          className="btn-primary w-full"
        >
          {isLoading ? "🔄 Searching..." : "🔍 Analyze"}
        </button>
        <p className="text-sage-600 text-xs font-medium">
          Search skincare and food products from our database
        </p>
      </form>
    );
  }

  return (
    <form onSubmit={handleSearch} className="w-full">
      <div className="flex gap-2">
        <input
          type="text"
          value={productName}
          onChange={(e) => setProductName(e.target.value)}
          placeholder="e.g., 'Neutrogena Sunscreen SPF 50' or 'Coca Cola'"
          className="input-field flex-1"
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading} className="btn-primary">
          {isLoading ? "Searching..." : "Search"}
        </button>
      </div>
      <p className="text-sage-600 text-xs mt-2 leading-relaxed font-medium">
        Searches skincare and food products. For direct ingredient analysis, use
        the "Analyze Ingredients" tab.
      </p>
    </form>
  );
}
