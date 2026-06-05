/**
 * downloadFile — helper for triggering browser file downloads from Blob responses.
 *
 * Used by features that consume endpoints returning binary attachments
 * (e.g. GET /equipos/exportar, GET /guardias/export) with Axios responseType:'blob'.
 *
 * No `any` — Blob is the correct type for binary axios responses.
 */

/**
 * Triggers a browser download of a Blob as a named file.
 *
 * @param blob - The Blob returned from the Axios response (responseType: 'blob')
 * @param filename - The suggested filename for the download (e.g. 'equipo.csv')
 */
export function downloadFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}
