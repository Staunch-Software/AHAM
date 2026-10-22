import { accuracyLabel, csvCell, fillDays, fmtDevice, validCoords } from '../src/services/format'

test('trend days: gaps are filled with zero and the axis ends on the latest known day', () => {
  const now = new Date(2026, 9, 20) // 20 Oct 2026, local
  const d = fillDays([{ date: '2026-10-16', count: 2 }, { date: '2026-10-17', count: 1 }], 14, now)
  expect(d).toHaveLength(14)
  expect(d[13]).toEqual({ date: '2026-10-20', count: 0 })
  expect(d[0].date).toBe('2026-10-07')
  expect(d.find((x) => x.date === '2026-10-16')?.count).toBe(2)
  expect(d.reduce((a, x) => a + x.count, 0)).toBe(3)
  // a company-timezone day later than the browser's today still ends the axis
  expect(fillDays([{ date: '2026-10-21', count: 4 }], 3, now).map((x) => x.date)).toEqual(['2026-10-19', '2026-10-20', '2026-10-21'])
  expect(fillDays([], 14, now)).toEqual([])
})

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
