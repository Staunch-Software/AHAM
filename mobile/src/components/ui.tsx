import { MaterialCommunityIcons } from '@expo/vector-icons'
import { type ComponentRef, forwardRef, type ReactNode } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Text, type TextProps, TextInput, type TextInputProps, View, type ViewStyle } from 'react-native'
import { C, F, RAG_STYLE } from '@/lib/theme'

export type IconName = keyof typeof MaterialCommunityIcons.glyphMap
export const Icon = ({ name, size = 20, color = C.navy700 }: { name: IconName; size?: number; color?: string }) => (
  <MaterialCommunityIcons name={name} size={size} color={color} />
)

type Tone = 'title' | 'h2' | 'body' | 'label' | 'small' | 'mono'
const TONES: Record<Tone, object> = {
  title: { fontFamily: F.bold, fontSize: 24, color: C.navy900, letterSpacing: -0.3 },
  h2: { fontFamily: F.semibold, fontSize: 16, color: C.navy900 },
  body: { fontFamily: F.regular, fontSize: 15, color: C.ink, lineHeight: 21 },
  label: { fontFamily: F.medium, fontSize: 13, color: C.muted },
  small: { fontFamily: F.regular, fontSize: 12, color: C.muted, lineHeight: 17 },
  mono: { fontFamily: F.semibold, fontSize: 13, color: C.navy700, letterSpacing: 0.2 },
}
export function T({ tone = 'body', style, ...p }: TextProps & { tone?: Tone }) {
  return <Text {...p} style={[TONES[tone], style]} />
}

type BtnVariant = 'primary' | 'gold' | 'secondary' | 'ghost' | 'danger'
export function Button({ title, onPress, variant = 'primary', icon, disabled, busy, style, testID }: {
  title: string; onPress?: () => void; variant?: BtnVariant; icon?: IconName; disabled?: boolean; busy?: boolean; style?: ViewStyle; testID?: string
}) {
  const bg = { primary: C.navy700, gold: C.gold500, secondary: C.white, ghost: 'transparent', danger: C.roof500 }[variant]
  const fg = { primary: C.white, gold: C.navy900, secondary: C.navy700, ghost: C.navy700, danger: C.white }[variant]
  return (
    <Pressable testID={testID} accessibilityRole="button" accessibilityState={{ disabled: !!disabled || !!busy }} disabled={disabled || busy} onPress={onPress}
      style={({ pressed }) => [s.btn, { backgroundColor: bg, opacity: disabled ? 0.45 : pressed ? 0.85 : 1 },
        variant === 'secondary' && { borderWidth: 1, borderColor: C.outline }, style]}>
      {busy ? <ActivityIndicator color={fg} /> : icon ? <Icon name={icon} color={fg} size={19} /> : null}
      <Text style={[s.btnText, { color: fg }]}>{title}</Text>
    </Pressable>
  )
}

export type InputRef = ComponentRef<typeof TextInput>
export const Field = forwardRef<InputRef, TextInputProps & { label: string; error?: string | null; hint?: string; right?: ReactNode }>(
  ({ label, error, hint, right, style, ...p }, ref) => (
    <View style={{ gap: 6 }}>
      <T tone="label">{label}</T>
      <View style={[s.input, error ? { borderColor: C.roof500 } : null, p.multiline && { minHeight: 96, alignItems: 'flex-start' }]}>
        <TextInput ref={ref} placeholderTextColor="#94A3B8" {...p}
          style={[{ flex: 1, fontFamily: F.regular, fontSize: 16, color: C.ink, paddingVertical: 12 }, p.multiline && { textAlignVertical: 'top' }, style]} />
        {right}
      </View>
      {error ? <T tone="small" style={{ color: C.roof700 }} accessibilityRole="alert">{error}</T> : hint ? <T tone="small">{hint}</T> : null}
    </View>
  ))

export const Card = ({ children, style, padded = true }: { children: ReactNode; style?: ViewStyle; padded?: boolean }) => (
  <View style={[s.card, padded && { padding: 16 }, style]}>{children}</View>
)

export function Chip({ label, selected, onPress, icon, hint }: { label: string; selected: boolean; onPress: () => void; icon?: IconName; hint?: string }) {
  return (
    <Pressable accessibilityRole="radio" accessibilityState={{ selected }} onPress={onPress}
      style={[s.chip, selected && { backgroundColor: C.navy700, borderColor: C.navy700 }]}>
      {icon && <Icon name={icon} size={18} color={selected ? C.gold400 : C.navy600} />}
      <View style={{ flexShrink: 1 }}>
        <Text style={[s.chipText, selected && { color: C.white }]}>{label}</Text>
        {hint && <Text style={[s.chipHint, selected && { color: C.navy200 }]}>{hint}</Text>}
      </View>
    </Pressable>
  )
}

export function RagBadge({ value }: { value: string }) {
  const r = RAG_STYLE[value] ?? RAG_STYLE.NA!
  return (
    <View style={[s.badge, { backgroundColor: r.bg }]}>
      <View style={[s.dot, { backgroundColor: r.fg }]} />
      <Text style={[s.badgeText, { color: r.fg }]}>{r.label}</Text>
    </View>
  )
}

export function Pill({ text, color = C.muted, bg = '#F1F5F9', icon }: { text: string; color?: string; bg?: string; icon?: IconName }) {
  return (
    <View style={[s.badge, { backgroundColor: bg }]}>
      {icon && <Icon name={icon} size={13} color={color} />}
      <Text style={[s.badgeText, { color }]}>{text}</Text>
    </View>
  )
}

export function Progress({ value, max, color = C.navy700 }: { value: number; max: number; color?: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0
  return (
    <View style={s.track} accessibilityRole="progressbar" accessibilityValue={{ min: 0, max, now: value }}>
      <View style={[s.bar, { width: `${pct}%`, backgroundColor: color }]} />
    </View>
  )
}

export function Banner({ tone = 'info', icon, children }: { tone?: 'info' | 'warn' | 'error' | 'ok'; icon?: IconName; children: ReactNode }) {
  const t = { info: [C.navy50, C.navy700], warn: [C.gold100, C.gold700], error: [C.roof50, C.roof700], ok: [C.green50, C.green700] }[tone]
  return (
    <View style={[s.banner, { backgroundColor: t[0] }]} accessibilityRole={tone === 'error' ? 'alert' : undefined}>
      {icon && <Icon name={icon} size={18} color={t[1]} />}
      <Text style={[s.bannerText, { color: t[1] }]}>{children}</Text>
    </View>
  )
}

export const Row = ({ children, style }: { children: ReactNode; style?: ViewStyle }) => (
  <View style={[{ flexDirection: 'row', alignItems: 'center', gap: 8 }, style]}>{children}</View>
)

const s = StyleSheet.create({
  btn: { minHeight: 50, borderRadius: 14, paddingHorizontal: 18, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  btnText: { fontFamily: F.semibold, fontSize: 16 },
  input: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: C.outline, borderRadius: 12, backgroundColor: C.white, paddingHorizontal: 14 },
  card: { backgroundColor: C.white, borderRadius: 18, borderWidth: 1, borderColor: C.line, shadowColor: '#0F172A', shadowOpacity: 0.05, shadowRadius: 8, shadowOffset: { width: 0, height: 2 }, elevation: 1 },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 12, paddingVertical: 10, borderRadius: 12, borderWidth: 1, borderColor: C.outline, backgroundColor: C.white, flexBasis: '48%', flexGrow: 1 },
  chipText: { fontFamily: F.semibold, fontSize: 14, color: C.navy900 },
  chipHint: { fontFamily: F.regular, fontSize: 11, color: C.muted },
  badge: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 9, paddingVertical: 3, borderRadius: 999, alignSelf: 'flex-start' },
  dot: { width: 6, height: 6, borderRadius: 3 },
  badgeText: { fontFamily: F.semibold, fontSize: 12 },
  track: { height: 8, borderRadius: 4, backgroundColor: C.navy100, overflow: 'hidden' },
  bar: { height: 8, borderRadius: 4 },
  banner: { flexDirection: 'row', gap: 10, alignItems: 'flex-start', padding: 12, borderRadius: 12 },
  bannerText: { flex: 1, fontFamily: F.medium, fontSize: 13, lineHeight: 18 },
})
