import { expect, test } from '@jest/globals'
import { normalizeServer } from '../src/lib/server'

test('the PC address as people type it becomes the full server address', () => {
  expect(normalizeServer('192.168.14.106')).toBe('http://192.168.14.106:8000')
  expect(normalizeServer(' 192.168.14.106:8000 ')).toBe('http://192.168.14.106:8000')
  expect(normalizeServer('http://192.168.14.106:8000/')).toBe('http://192.168.14.106:8000')
  expect(normalizeServer('HTTP://pc.local:9000')).toBe('http://pc.local:9000')
  expect(normalizeServer('https://sankalp.aham.in')).toBe('https://sankalp.aham.in')
})

test('anything that is not an address is refused', () => {
  for (const bad of ['', '   ', '192.168.14.106:99999', '192.168 14 106', 'http://', 'ftp://192.168.1.2', '192.168.1.2/api', 'http://a..b']) {
    expect(normalizeServer(bad)).toBeNull()
  }
})
