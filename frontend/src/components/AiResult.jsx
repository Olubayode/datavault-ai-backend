import Plot from "react-plotly.js";

function parseFigure(figureJson) {
  if (!figureJson) return null;
  try {
    return typeof figureJson === "string" ? JSON.parse(figureJson) : figureJson;
  } catch {
    return null;
  }
}

function formatCell(value) {
  if (value === null || value === undefined || value === "") return "None";
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}

export function parseAiResult(chat) {
  const value = chat?.ai_result || chat?.ai_response || chat;
  if (!value) return null;
  if (typeof value === "object") return value;

  try {
    const parsed = JSON.parse(value);
    if (parsed && typeof parsed === "object" && ("answer" in parsed || "tables" in parsed || "charts" in parsed)) {
      return parsed;
    }
  } catch {
    return null;
  }

  return null;
}

export default function AiResult({ result }) {
  if (!result) return null;

  return (
    <div className="ai-result">
      {result.answer && <p className="ai-answer">{result.answer}</p>}

      {result.analysis_model && (
        <div className="ai-meta">
          <span>{result.analysis_mode || "ai_analysis"}</span>
          <span>{result.analysis_model}</span>
        </div>
      )}

      {result.insights?.length > 0 && (
        <section className="ai-section">
          <h3>Insights</h3>
          <ul className="insight-list">
            {result.insights.map((insight, index) => (
              <li key={`${insight}-${index}`}>{insight}</li>
            ))}
          </ul>
        </section>
      )}

      {result.tables?.length > 0 && (
        <section className="ai-section">
          <h3>Tables</h3>
          <div className="ai-table-stack">
            {result.tables.map((table, index) => (
              <article className="ai-table-block" key={`${table.title || "table"}-${index}`}>
                <div className="ai-table-copy">
                  <h4>{table.title || "Table"}</h4>
                  {table.description && <p>{table.description}</p>}
                  {table.interpretation && <p className="table-interpretation">{table.interpretation}</p>}
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        {(table.columns || Object.keys(table.rows?.[0] || {})).map((column) => (
                          <th key={column}>{column}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(table.rows || []).slice(0, 20).map((row, rowIndex) => (
                        <tr key={rowIndex}>
                          {(table.columns || Object.keys(row)).map((column) => (
                            <td key={column}>{formatCell(row?.[column])}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {result.charts?.length > 0 && (
        <section className="ai-section">
          <h3>Charts</h3>
          <div className="ai-chart-stack">
            {result.charts.map((chart, index) => {
              const fig = parseFigure(chart.figure_json);
              if (!fig) return null;

              return (
                <article className="ai-chart-block" key={`${chart.title || "chart"}-${index}`}>
                  <h4>{chart.title || "Chart"}</h4>
                  <Plot
                    data={fig.data || []}
                    layout={{
                      ...(fig.layout || {}),
                      autosize: true,
                      margin: { t: 48, r: 24, b: 56, l: 64, ...(fig.layout?.margin || {}) },
                    }}
                    config={{ displaylogo: false, responsive: true }}
                    style={{ width: "100%", height: "420px" }}
                    useResizeHandler
                  />
                </article>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
