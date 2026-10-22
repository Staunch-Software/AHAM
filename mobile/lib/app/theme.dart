import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Light status-bar icons for screens that start with the dark navy header (login, home).
const lightStatusBar = SystemUiOverlayStyle(statusBarColor: Colors.transparent, statusBarIconBrightness: Brightness.light, statusBarBrightness: Brightness.dark);

/// AHAM Housing Finance brand colours: deep navy (logo navy #283079), gold accent and the red of the logo roof.
class Brand {
  static const navy900 = Color(0xFF17153A);
  static const navy800 = Color(0xFF1E1B4B);
  static const navy700 = Color(0xFF283079);
  static const navy600 = Color(0xFF364090);
  static const navy200 = Color(0xFFC8CCE8);
  static const navy100 = Color(0xFFE4E6F4);
  static const navy50 = Color(0xFFF2F3FA);
  static const gold500 = Color(0xFFEAB308);
  static const gold400 = Color(0xFFFACC15);
  static const gold100 = Color(0xFFFEF9C3);
  static const gold700 = Color(0xFFA16207);
  static const roof500 = Color(0xFFED2636);
  static const roof700 = Color(0xFFB01A27);
  static const roof50 = Color(0xFFFFF1F2);
  static const roof200 = Color(0xFFFFC6CA);
  static const green600 = Color(0xFF059669);
  static const green50 = Color(0xFFECFDF5);
  static const page = Color(0xFFF1F3F9);
  static const line = Color(0xFFE2E8F0);
  static const ink = Color(0xFF1E293B);
  static const muted = Color(0xFF64748B);
}

const _radius = 14.0;

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: Brand.navy700).copyWith(
    primary: Brand.navy700,
    onPrimary: Colors.white,
    primaryContainer: Brand.navy100,
    onPrimaryContainer: Brand.navy900,
    secondary: Brand.gold500,
    onSecondary: Brand.navy900,
    secondaryContainer: Brand.gold100,
    onSecondaryContainer: Brand.navy900,
    error: Brand.roof700,
    onError: Colors.white,
    errorContainer: Brand.roof50,
    onErrorContainer: Brand.roof700,
    surface: Colors.white,
    onSurface: Brand.ink,
    outline: const Color(0xFFCBD5E1),
    outlineVariant: Brand.line,
  );

  final base = ThemeData(useMaterial3: true, colorScheme: scheme, fontFamily: 'Inter');
  final text = base.textTheme.copyWith(
    headlineMedium: base.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700, color: Brand.navy900, letterSpacing: -0.5),
    headlineSmall: base.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700, color: Brand.navy900, letterSpacing: -0.3),
    titleLarge: base.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700, color: Brand.navy900, letterSpacing: -0.2),
    titleMedium: base.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600, color: Brand.navy900),
    titleSmall: base.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600, color: Brand.navy900),
    labelLarge: base.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w600),
  );

  OutlineInputBorder border(Color c, [double w = 1]) => OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: c, width: w));
  final shape = RoundedRectangleBorder(borderRadius: BorderRadius.circular(12));

  return base.copyWith(
    textTheme: text,
    scaffoldBackgroundColor: Brand.page,
    appBarTheme: AppBarTheme(
      backgroundColor: Colors.white,
      foregroundColor: Brand.navy900,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      systemOverlayStyle: SystemUiOverlayStyle.dark.copyWith(statusBarColor: Colors.transparent), // dark clock/icons on the white bar
      titleTextStyle: text.titleLarge?.copyWith(fontSize: 19),
      shape: const Border(bottom: BorderSide(color: Brand.line)),
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      margin: EdgeInsets.zero,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(_radius + 2), side: const BorderSide(color: Brand.line)),
    ),
    dividerTheme: const DividerThemeData(color: Brand.line, thickness: 1, space: 1),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
      labelStyle: const TextStyle(color: Brand.muted),
      floatingLabelStyle: const TextStyle(color: Brand.navy700, fontWeight: FontWeight.w600),
      border: border(const Color(0xFFCBD5E1)),
      enabledBorder: border(const Color(0xFFCBD5E1)),
      focusedBorder: border(Brand.navy700, 2),
      errorBorder: border(Brand.roof500),
      focusedErrorBorder: border(Brand.roof500, 2),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: Brand.navy700,
        foregroundColor: Colors.white,
        disabledBackgroundColor: const Color(0xFFCBD5E1),
        minimumSize: const Size(0, 50),
        padding: const EdgeInsets.symmetric(horizontal: 20),
        shape: shape,
        textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15, fontFamily: 'Inter'),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: Brand.navy700,
        minimumSize: const Size(0, 46),
        side: const BorderSide(color: Color(0xFFCBD5E1)),
        shape: shape,
        textStyle: const TextStyle(fontWeight: FontWeight.w600, fontFamily: 'Inter'),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: Brand.navy700, textStyle: const TextStyle(fontWeight: FontWeight.w600, fontFamily: 'Inter')),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      surfaceTintColor: Colors.transparent,
      elevation: 8,
      shadowColor: Brand.navy900.withValues(alpha: 0.25),
      height: 68,
      indicatorColor: Brand.navy100,
      labelTextStyle: WidgetStateProperty.resolveWith((s) => TextStyle(
            fontSize: 12,
            fontWeight: s.contains(WidgetState.selected) ? FontWeight.w700 : FontWeight.w500,
            color: s.contains(WidgetState.selected) ? Brand.navy700 : Brand.muted,
            fontFamily: 'Inter',
          )),
      iconTheme: WidgetStateProperty.resolveWith((s) => IconThemeData(color: s.contains(WidgetState.selected) ? Brand.navy700 : Brand.muted, size: 24)),
    ),
    chipTheme: base.chipTheme.copyWith(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)), side: const BorderSide(color: Brand.line)),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: Brand.navy900,
      contentTextStyle: const TextStyle(color: Colors.white, fontFamily: 'Inter'),
      shape: shape,
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: Colors.white,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
    listTileTheme: const ListTileThemeData(contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 4)),
  );
}
