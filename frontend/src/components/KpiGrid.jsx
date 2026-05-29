import { Activity, BarChart3, Database, Sparkles } from "lucide-react";

const icons = [Database, BarChart3, Activity, Sparkles];

export default function KpiGrid({ summary }) {
  const items = [
    { label: "Rows", value: summary?.rows ?? 0 },
    { label: "Columns", value: summary?.columns ?? 0 },
    ...(summary?.kpis ?? []),
  ].slice(0, 4);

  return (
    <div className="kpi-grid">
      {items.map((item, index) => {
        const Icon = icons[index] || Activity;
        return (
          <div className="metric" key={`${item.label}-${index}`}>
            <Icon size={18} />
            <span>{item.label}</span>
            <strong>{Number(item.value).toLocaleString()}</strong>
          </div>
        );
      })}
    </div>
  );
}
