import { accuracyLabel, csvCell, fmtDevice, validCoords } from '../src/services/format'

test('unavailable coordinates are not zero; zero is valid', () => {
  expect(validCoords(null, null)).toBe(false)
  expect(validCoords(0, 0)).toBe(true)
  expect(validCoords(91, 0)).toBe(false)
  expect(validCoords(10, 181)).toBe(false)
})
test('device time is rendered in the agent offset', () => {
  expect(fmtDevice('2026-10-10T04:30:00Z', 330)).toBe('2026-10-10 10:00:00 (UTC+05:30)')
  expect(fmtDevice(null, 330)).toBe('—')
})
test('csv cells neutralise formulas and escape', () => {
  expect(csvCell('=HYPERLINK("x")')).toBe('"\'=HYPERLINK(""x"")"')
  expect(csvCell('a,b')).toBe('"a,b"')
  expect(csvCell(null)).toBe('')
})
test('poor accuracy is flagged', () => {
  expect(accuracyLabel(12.4)).toBe('±12 m')
  expect(accuracyLabel(250)).toContain('poor')
  expect(accuracyLabel(null)).toBe('accuracy unknown')
})
