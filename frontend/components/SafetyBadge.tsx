/**
 * Safety Badge Component
 * Displays ingredient safety rating with color coding
 */
interface SafetyBadgeProps {
  rating: string;
  score?: number;
}

export default function SafetyBadge({ rating, score }: SafetyBadgeProps) {
  const getColorAndIcon = (rating: string) => {
    switch (rating.toUpperCase()) {
      case "SAFE":
        return {
          bg: "bg-gradient-to-br from-green-100 to-green-50",
          border: "border-green-300",
          text: "text-green-900",
          icon: "✓",
          label: "Safe",
          accent: "bg-green-500",
        };
      case "CAUTION":
        return {
          bg: "bg-gradient-to-br from-yellow-100 to-yellow-50",
          border: "border-yellow-300",
          text: "text-yellow-900",
          icon: "!",
          label: "Caution",
          accent: "bg-yellow-500",
        };
      case "HARMFUL":
        return {
          bg: "bg-gradient-to-br from-red-100 to-red-50",
          border: "border-red-300",
          text: "text-red-900",
          icon: "⚠",
          label: "Harmful",
          accent: "bg-red-500",
        };
      default:
        return {
          bg: "bg-gradient-to-br from-sage-100 to-sage-50",
          border: "border-sage-300",
          text: "text-sage-900",
          icon: "?",
          label: "Unknown",
          accent: "bg-sage-500",
        };
    }
  };

  const colors = getColorAndIcon(rating);

  return (
    <div
      className={`${colors.bg} ${colors.border} border-l-4 rounded-lg px-5 py-4 inline-block shadow-sm`}
    >
      <div className="flex items-center gap-3">
        <div
          className={`${colors.accent} w-10 h-10 rounded-full flex items-center justify-center text-white font-bold flex-shrink-0`}
        >
          {colors.icon}
        </div>
        <div>
          <p className={`${colors.text} font-bold text-base`}>{colors.label}</p>
          {score !== undefined && (
            <p
              className={`${colors.text} text-xs mt-0.5 opacity-80 font-medium`}
            >
              Score: {score.toFixed(1)}/100
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
