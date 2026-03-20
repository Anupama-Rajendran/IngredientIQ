/**
 * Ingredient Card Component
 * Displays detailed information about a single ingredient analysis
 */
interface IngredientCardProps {
  ingredient: {
    ingredient_name: string;
    safety_rating: string;
    reasoning: string;
    hazards: string[];
    sources: string[];
    evidence: any[];
    confidence_score: number;
  };
}

export default function IngredientCard({ ingredient }: IngredientCardProps) {
  const getSafetyColor = (rating: string) => {
    switch (rating.toUpperCase()) {
      case "SAFE":
        return {
          bg: "bg-green-50",
          border: "border-green-200",
          accent: "bg-green-100",
        };
      case "CAUTION":
        return {
          bg: "bg-yellow-50",
          border: "border-yellow-200",
          accent: "bg-yellow-100",
        };
      case "HARMFUL":
        return {
          bg: "bg-red-50",
          border: "border-red-200",
          accent: "bg-red-100",
        };
      default:
        return {
          bg: "bg-sage-50",
          border: "border-sage-200",
          accent: "bg-sage-100",
        };
    }
  };

  const getBadgeColor = (rating: string) => {
    switch (rating.toUpperCase()) {
      case "SAFE":
        return "bg-green-100 text-green-900 border border-green-300";
      case "CAUTION":
        return "bg-yellow-100 text-yellow-900 border border-yellow-300";
      case "HARMFUL":
        return "bg-red-100 text-red-900 border border-red-300";
      default:
        return "bg-sage-100 text-forest-900 border border-sage-300";
    }
  };

  return (
    <div
      className={`border-l-4 rounded-lg p-6 ${getSafetyColor(ingredient.safety_rating).bg} ${getSafetyColor(ingredient.safety_rating).border} border hover:shadow-md transition-all`}
    >
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-serif font-bold text-forest-800 capitalize mb-1">
            {ingredient.ingredient_name}
          </h3>
          <span
            className={`inline-block text-xs px-3 py-1.5 rounded-full font-bold ${getBadgeColor(ingredient.safety_rating)}`}
          >
            {ingredient.safety_rating}
          </span>
        </div>
      </div>

      <p className="text-sage-800 text-sm leading-relaxed mb-4 font-medium">
        {ingredient.reasoning}
      </p>

      {ingredient.hazards && ingredient.hazards.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-bold text-forest-700 mb-2 uppercase tracking-wide">
            Hazards
          </p>
          <div className="flex flex-wrap gap-2">
            {ingredient.hazards.map((hazard, idx) => (
              <span
                key={idx}
                className="text-xs bg-white px-3 py-1.5 rounded-full border border-sage-300 text-forest-700 font-medium"
              >
                {hazard}
              </span>
            ))}
          </div>
        </div>
      )}

      {ingredient.sources && ingredient.sources.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-bold text-forest-700 mb-2 uppercase tracking-wide">
            Sources
          </p>
          <p className="text-xs text-sage-700 leading-relaxed font-medium">
            {ingredient.sources.join(", ")}
          </p>
        </div>
      )}

      <div className="flex items-center gap-3 pt-2 border-t border-sage-300">
        <div className="flex-1 mt-2">
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs font-semibold text-forest-700">
              Confidence
            </span>
            <span className="text-xs font-bold text-forest-700">
              {(ingredient.confidence_score * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-sage-300 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                ingredient.confidence_score > 0.8
                  ? "bg-green-600"
                  : ingredient.confidence_score > 0.5
                    ? "bg-forest-600"
                    : "bg-sage-400"
              }`}
              style={{ width: `${ingredient.confidence_score * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
