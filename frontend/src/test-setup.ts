import '@testing-library/jest-dom'

// Polyfill Blob.prototype.text() for JSDOM environments that lack it.
// JSDOM's Blob does not implement the text() method (Web API) — add it here
// so tests that call blob.text() work correctly.
if (typeof Blob !== 'undefined' && !Blob.prototype.text) {
  Blob.prototype.text = function (): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = () => reject(reader.error)
      reader.readAsText(this)
    })
  }
}
