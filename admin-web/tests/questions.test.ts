import { describe, expect, test } from 'vitest'
import { questionApplies } from '../src/services/classify'

describe('call questions follow the loan need (7.2, as the Takeoff call sheet)', () => {
  test('loan questions only for a loan', () => {
    for (const need of ['LAP', 'BT + LAP', 'Not looking for a loan', undefined]) {
      expect(questionApplies('timeline', need)).toBe(false)
      expect(questionApplies('next_step', need)).toBe(false)
    }
    expect(questionApplies('timeline', 'Balance transfer')).toBe(true)
    expect(questionApplies('loan_need', undefined)).toBe(true)
  })
  test('own contribution only for a purchase or construction', () => {
    expect(questionApplies('own_contribution', 'Home purchase')).toBe(true)
    expect(questionApplies('own_contribution', 'Plot + construction')).toBe(true)
    expect(questionApplies('own_contribution', 'Improvement or extension')).toBe(false)
    expect(questionApplies('own_contribution', 'Balance transfer')).toBe(false)
  })
})
