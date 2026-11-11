/**
 * The server address a person types on the phone: "192.168.1.20", "192.168.1.20:8000" or "http://192.168.1.20:8000".
 * Returns the full address (port 8000 when none is given for http), or null when it is not an address.
 */
export function normalizeServer(input: string): string | null {
  let s = input.trim().replace(/\/+$/, '')
  if (!s) return null
  if (!/^https?:\/\//i.test(s)) s = `http://${s}`
  const m = /^(https?):\/\/([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*)(?::(\d{1,5}))?$/i.exec(s)
  if (!m) return null
  const scheme = m[1].toLowerCase()
  const port = m[3] ? Number(m[3]) : null
  if (port !== null && (port < 1 || port > 65535)) return null
  if (port !== null) return `${scheme}://${m[2]}:${port}`
  return scheme === 'https' ? `https://${m[2]}` : `http://${m[2]}:8000`
}
