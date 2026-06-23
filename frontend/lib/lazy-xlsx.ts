let _xlsx: typeof import("xlsx") | null = null

export async function getXLSX() {
  if (!_xlsx) {
    _xlsx = await import("xlsx")
  }
  return _xlsx
}
