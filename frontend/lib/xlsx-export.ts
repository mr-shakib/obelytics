import { getXLSX } from "@/lib/lazy-xlsx"

export type XlsxColumn<T> = {
  key: string
  header: string
  value?: (row: T) => string | number | null | undefined
}

/**
 * Write `rows` to an .xlsx file the browser downloads immediately.
 * Columns drive both the header row and the cell order.
 */
export async function exportToXlsx<T extends Record<string, unknown>>({
  fileName,
  sheetName,
  columns,
  rows,
}: {
  fileName: string
  sheetName: string
  columns: XlsxColumn<T>[]
  rows: T[]
}) {
  const XLSX = await getXLSX()
  const body = rows.map((row) =>
    columns.map((col) => {
      const raw = col.value ? col.value(row) : row[col.key]
      return raw == null ? "" : (raw as string | number)
    })
  )
  const ws = XLSX.utils.aoa_to_sheet([columns.map((c) => c.header), ...body])
  ws["!cols"] = columns.map(() => ({ wch: 24 }))
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, sheetName)
  XLSX.writeFile(wb, fileName)
}
