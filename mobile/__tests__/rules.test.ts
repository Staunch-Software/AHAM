import { expect, test } from '@jest/globals'
import { addDaysIso, cleanPhone, countDate, entryCode, isValidPhone, istDate, kekaTime, phoneProblem } from '../src/lib/rules'

// Same cases as backend/tests/test_entry_rules.py: the phone and the server must agree.
test.each([
  ['9876543210', '9876543210', true],
  ['+91 98765 43210', '9876543210', true],
  ['+91-98765-43210', '9876543210', true],
  ['919876543210', '9876543210', true],
  ['09876543210', '9876543210', true],
  ['9876543210.0', '9876543210', true],
  ['98765​43210', '9876543210', true],
  ['5876543210', '5876543210', false],
  ['98765', '98765', false],
  ['98765432101', '98765432101', false],
  ['abc', '', false],
] as [string, string, boolean][])('phone %s -> %s (valid %s)', (raw, clean, valid) => {
  expect(cleanPhone(raw)).toBe(clean)
  expect(isValidPhone(cleanPhone(raw))).toBe(valid)
})

test('phone problems are explained', () => {
  expect(phoneProblem('')).toMatch(/Enter/)
  expect(phoneProblem('12345')).toMatch(/10 digits/)
  expect(phoneProblem('5876543210')).toMatch(/6, 7, 8 or 9/)
  expect(phoneProblem('+91 98765 43210')).toBeNull()
})

test('Entry ID is built in IST and truncated to the second', () => {
  const t = new Date(Date.UTC(2026, 9, 15, 3, 37, 6, 999)) // 09:07:06.999 IST
  expect(entryCode('ahfl01810', t)).toBe('AHFL01810-20261015-090706')
  const late = new Date(Date.UTC(2026, 9, 15, 19, 0, 0)) // 00:30 IST next day
  expect(entryCode('X', late)).toBe('X-20261016-003000')
  expect(istDate(late)).toBe('2026-10-16')
})

test('Keka photo time is optional HH:MM', () => {
  expect(kekaTime('')).toBeNull()
  expect(kekaTime('9:05')).toBe('09:05:00')
  expect(kekaTime('23:59')).toBe('23:59:00')
  expect(() => kekaTime('24:00')).toThrow()
  expect(() => kekaTime('9.05')).toThrow()
})

test('count date: Sundays and holidays move to the next working day, as on the server (4.4)', () => {
  const none = new Set<string>()
  expect(countDate('2026-10-24', none)).toBe('2026-10-24') // Saturday counts
  expect(countDate('2026-10-25', none)).toBe('2026-10-26') // Sunday -> Monday
  expect(countDate('2026-10-25', new Set(['2026-10-26']))).toBe('2026-10-27') // Sunday then a holiday Monday
  expect(countDate('2026-10-22', new Set(['2026-10-22']))).toBe('2026-10-23')
  expect(addDaysIso('2026-10-31', 1)).toBe('2026-11-01')
})
