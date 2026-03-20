/**
 * Product Analysis Results Component
 */
import SafetyBadge from "./SafetyBadge";
import IngredientCard from "./IngredientCard";

interface ProductAnalysisProps {
  analysis: {
    overall_rating: string;
    overall_score: number;
    ingredient_count: number;
    safety_summary: Record<string, number>;
    ingredients: any[];
  };
}

export default function ProductAnalysisResults({
  analysis,
}: ProductAnalysisProps) {
  return (
    <div className="space-y-8">
      {/* Header with Logo */}
      <div className="flex items-center gap-3 mb-8">
        <div>
          <h1 className="text-3xl font-serif font-bold text-forest-800">
            IngredientIQ Results
          </h1>
          <p className="text-sage-600 text-xs font-semibold mt-0.5">
            Safety, Simplified
          </p>
        </div>
      </div>

      {/* Overall Score Section */}
      <div className="bg-white rounded-xl border border-sage-200 p-8 shadow-sm">
        <h2 className="text-3xl font-serif font-bold text-forest-800 mb-8">
          Safety Analysis Results
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
          <div className="flex items-center gap-6">
            <div className="w-32 h-32 rounded-full bg-gradient-to-br from-forest-700 to-forest-600 flex items-center justify-center shadow-lg">
              <div className="text-center">
                <div className="text-4xl font-bold text-white">
                  {analysis.overall_score.toFixed(0)}
                </div>
                <div className="text-xs text-sage-100 mt-1 font-semibold">
                  Score
                </div>
              </div>
            </div>
            <div>
              <p className="text-sage-700 text-sm font-semibold mb-2">
                Overall Rating
              </p>
              <SafetyBadge
                rating={analysis.overall_rating}
                score={analysis.overall_score}
              />
              <p className="text-sage-700 text-sm mt-3 font-medium">
                <strong className="text-forest-800">
                  {analysis.ingredient_count}
                </strong>{" "}
                ingredients analyzed
              </p>
            </div>
          </div>

          {/* Safety Summary Stats */}
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(analysis.safety_summary).map(([rating, count]) => {
              const colorMap: Record<
                string,
                { bg: string; text: string; emoji: string }
              > = {
                SAFE: { bg: "bg-green-50", text: "text-green-700", emoji: "✓" },
                CAUTION: {
                  bg: "bg-yellow-50",
                  text: "text-yellow-700",
                  emoji: "!",
                },
                HARMFUL: { bg: "bg-red-50", text: "text-red-700", emoji: "⚠" },
              };
              const colors = colorMap[rating] || {
                bg: "bg-sage-50",
                text: "text-sage-700",
                emoji: "?",
              };

              return (
                <div
                  key={rating}
                  className={`${colors.bg} rounded-lg p-4 border border-sage-200 text-center`}
                >
                  <p className={`text-2xl font-bold ${colors.text}`}>{count}</p>
                  <p className="text-xs font-semibold text-sage-600 mt-1">
                    {rating}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Ingredients Section */}
      <div>
        <h3 className="text-2xl font-serif font-bold text-forest-800 mb-6">
          Ingredient Details
        </h3>
        <div className="space-y-4">
          {analysis.ingredients.map((ingredient, idx) => (
            <IngredientCard key={idx} ingredient={ingredient} />
          ))}
        </div>
      </div>
    </div>
  );
}
