import 'package:flutter/material.dart';

import 'theme.dart';

/// The AHAM logo in a white rounded tile (the supplied logo has a white background).
class BrandLogo extends StatelessWidget {
  const BrandLogo({super.key, this.size = 44});
  final double size;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(size * 0.27),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.18), blurRadius: 10, offset: const Offset(0, 3))],
        ),
        clipBehavior: Clip.antiAlias,
        child: Image.asset('assets/images/aham-logo.jpg', fit: BoxFit.cover, semanticLabel: 'AHAM Housing Finance'),
      );
}

/// Tones used across the app: 'good' (accepted), 'bad' (needs attention), 'done' (finished, nothing to do), anything else = waiting.
({Color fg, Color bg}) toneColors(String tone) => switch (tone) {
      'good' => (fg: const Color(0xFF047857), bg: Brand.green50),
      'bad' => (fg: Brand.roof700, bg: Brand.roof50),
      'done' => (fg: const Color(0xFF475569), bg: const Color(0xFFF1F5F9)),
      _ => (fg: const Color(0xFF92400E), bg: const Color(0xFFFEF3C7)),
    };

IconData toneIcon(String tone) => switch (tone) {
      'good' => Icons.check_circle_rounded,
      'bad' => Icons.error_rounded,
      'done' => Icons.verified_rounded,
      _ => Icons.schedule_rounded,
    };

/// Small coloured pill with a status dot, for submission states.
class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.label, required this.tone});
  final String label;
  final String tone;

  @override
  Widget build(BuildContext context) {
    final c = toneColors(tone);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: c.bg, borderRadius: BorderRadius.circular(999)),
      child: Row(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(padding: const EdgeInsets.only(top: 5), child: Container(width: 7, height: 7, decoration: BoxDecoration(color: c.fg, shape: BoxShape.circle))),
        const SizedBox(width: 6),
        Flexible(child: Text(label, style: TextStyle(color: c.fg, fontWeight: FontWeight.w600, fontSize: 12.5, height: 1.25))),
      ]),
    );
  }
}

/// Rounded tinted square holding an icon.
class IconTile extends StatelessWidget {
  const IconTile({super.key, required this.icon, this.fg = Brand.navy700, this.bg = Brand.navy50, this.size = 44});
  final IconData icon;
  final Color fg;
  final Color bg;
  final double size;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(size * 0.3)),
        child: Icon(icon, color: fg, size: size * 0.5),
      );
}

String initialsOf(String name) {
  final parts = name.trim().split(RegExp(r'\s+')).where((p) => p.isNotEmpty).take(2).toList();
  return parts.isEmpty ? '?' : parts.map((p) => p[0].toUpperCase()).join();
}

/// Message box with an icon: 'bad' = something the agent must act on, 'warn' = for information.
class Notice extends StatelessWidget {
  const Notice({super.key, required this.child, this.tone = 'warn', this.icon});
  final Widget child;
  final String tone;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final bad = tone == 'bad';
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: bad ? Brand.roof50 : Brand.gold100.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: bad ? Brand.roof200 : Brand.gold400.withValues(alpha: 0.5)),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon ?? (bad ? Icons.error_outline_rounded : Icons.info_outline_rounded), size: 20, color: bad ? Brand.roof700 : Brand.gold700),
        const SizedBox(width: 10),
        Expanded(child: DefaultTextStyle.merge(style: TextStyle(color: bad ? Brand.roof700 : const Color(0xFF713F12), fontSize: 13.5, height: 1.4), child: child)),
      ]),
    );
  }
}
