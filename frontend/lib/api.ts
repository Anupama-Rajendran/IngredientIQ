// React API client for communicating with IngredientIQ backend.

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

async function request(endpoint: string, options: RequestInit = {}) {
  const url = `${API_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("API request failed:", error);
    throw error;
  }
}

export const api = {
  health: () => request("/health"),

  analyzeProduct: (productName: string) =>
    request("/api/v1/analyze-product", {
      method: "POST",
      body: JSON.stringify({ product_name: productName }),
    }),

  analyzeIngredients: (ingredients: string[]) =>
    request("/api/v1/analyze-ingredients", {
      method: "POST",
      body: JSON.stringify({ ingredients }),
    }),

  analyzeImage: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    return fetch(`${API_URL}/api/v1/analyze-image`, {
      method: "POST",
      body: formData,
    })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) {
          const errorMsg =
            data?.detail ||
            `Image analysis failed: ${res.status} ${res.statusText}`;
          throw new Error(errorMsg);
        }
        return data;
      })
      .catch((error) => {
        console.error("Image analysis error:", error);
        throw error;
      });
  },

  searchIngredient: (ingredientName: string) =>
    request(
      `/api/v1/ingredient-search?ingredient_name=${encodeURIComponent(ingredientName)}`,
    ),

  listTools: () => request("/api/v1/tools"),

  getKBStats: () => request("/api/v1/knowledge-base-stats"),
};
