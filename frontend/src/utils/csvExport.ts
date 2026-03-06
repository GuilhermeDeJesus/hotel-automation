/**
 * Utilitários para exportar dados em CSV.
 */

function escapeCsvValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "";
  const str = String(value);
  if (str.includes(",") || str.includes('"') || str.includes("\n") || str.includes("\r")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/**
 * Gera CSV a partir de array de objetos e dispara download.
 */
export function downloadCsv(
  rows: Record<string, string | number | null | undefined>[],
  filename: string,
  columns?: string[]
): void {
  if (rows.length === 0 && !columns?.length) return;

  const headers = columns ?? (rows.length > 0 ? Object.keys(rows[0]) : []);
  const headerRow = headers.map(escapeCsvValue).join(",");
  const dataRows = rows.map((row) =>
    headers.map((col) => escapeCsvValue(row[col])).join(",")
  );
  const csv = [headerRow, ...dataRows].join("\r\n");

  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
