import { accuracyLabel, csvCell, fmtDevice, nextDateRange, validCoords } from '../src/services/format'

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
test('a call\'s Next date runs from tomorrow up to 30 working days, Sundays not counted (Takeoff master)', () => {
  // Wednesday 11 Nov 2026: Thursday 12 Nov to Wednesday 16 Dec
  expect(nextDateRange(new Date(2026, 10, 11))).toEqual({ min: '2026-11-12', max: '2026-12-16' })
  // Saturday 14 Nov: tomorrow is a Sunday, which is not counted
  expect(nextDateRange(new Date(2026, 10, 14))).toEqual({ min: '2026-11-15', max: '2026-12-19' })
})
