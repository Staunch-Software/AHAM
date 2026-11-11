/** AHAM brand (same tokens as the web portals, docs/design-system.md). */
export const C = {
  navy900: '#17153A', navy800: '#1E1B4B', navy700: '#283079', navy600: '#364090', navy200: '#C8CCE8', navy100: '#E4E6F4', navy50: '#F2F3FA',
  gold700: '#A16207', gold500: '#EAB308', gold400: '#FACC15', gold100: '#FEF9C3',
  roof700: '#B01A27', roof500: '#ED2636', roof200: '#FFC6CA', roof50: '#FFF1F2',
  green700: '#047857', green600: '#059669', green50: '#ECFDF5',
  amber700: '#B45309', amber50: '#FFFBEB', violet700: '#6D28D9', violet50: '#F5F3FF', sky700: '#0369A1', sky50: '#F0F9FF',
  page: '#F1F3F9', line: '#E2E8F0', outline: '#CBD5E1', ink: '#1E293B', muted: '#64748B', white: '#FFFFFF',
}

/** Inter is bundled (expo-font config plugin) so the app looks the same offline. */
export const F = { regular: 'Inter-Regular', medium: 'Inter-Medium', semibold: 'Inter-SemiBold', bold: 'Inter-Bold' }

export const RAG_STYLE: Record<string, { bg: string; fg: string; label: string }> = {
  GREEN: { bg: C.green50, fg: C.green700, label: 'Green' },
  AMBER: { bg: C.amber50, fg: C.amber700, label: 'Amber' },
  RED: { bg: C.roof50, fg: C.roof700, label: 'Red' },
  RNR: { bg: C.violet50, fg: C.violet700, label: 'No answer' },
  NA: { bg: '#F1F5F9', fg: C.muted, label: 'Not applicable' },
  PENDING: { bg: C.sky50, fg: C.sky700, label: 'Not called yet' },
}
