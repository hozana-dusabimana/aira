import 'package:flutter/material.dart';

/// Brand color tokens used across screens & widgets.
class AiraColors {
  static const navy = Color(0xFF0F172A);
  static const primary = Color(0xFF1E40AF); // RNP-ish navy blue
  static const primaryDark = Color(0xFF1D3FA0);
  static const accent = Color(0xFF2563EB);
  static const success = Color(0xFF10B981);
  static const warning = Color(0xFFF59E0B);
  static const danger = Color(0xFFEF4444);
  static const orange = Color(0xFFF97316);
  static const surfaceMuted = Color(0xFFF1F5F9);
  static const surface = Color(0xFFFFFFFF);
  static const textMuted = Color(0xFF64748B);
}

/// Severity → color mapping shared by all screens.
Color severityColor(String severity) {
  switch (severity.toLowerCase()) {
    case 'critical':
      return AiraColors.danger;
    case 'high':
      return AiraColors.orange;
    case 'medium':
      return AiraColors.warning;
    case 'low':
    default:
      return AiraColors.textMuted;
  }
}

/// Status → color mapping shared by all screens.
Color statusColor(String status) {
  switch (status.toLowerCase()) {
    case 'pending':
    case 'analyzing':
      return AiraColors.warning;
    case 'verified':
    case 'assigned':
    case 'in_progress':
      return AiraColors.accent;
    case 'resolved':
      return AiraColors.success;
    case 'rejected':
      return AiraColors.danger;
    default:
      return AiraColors.textMuted;
  }
}

ThemeData buildAppTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: AiraColors.primary,
    brightness: Brightness.light,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: const Color(0xFFF8FAFC),
    appBarTheme: const AppBarTheme(
      centerTitle: false,
      elevation: 0,
      backgroundColor: AiraColors.surface,
      foregroundColor: AiraColors.navy,
      titleTextStyle: TextStyle(
        color: AiraColors.navy,
        fontSize: 18,
        fontWeight: FontWeight.w600,
      ),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      color: AiraColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: Colors.grey.shade200),
      ),
      margin: EdgeInsets.zero,
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: Colors.grey.shade300),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: Colors.grey.shade300),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AiraColors.primary, width: 1.5),
      ),
      filled: true,
      fillColor: AiraColors.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 18),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        backgroundColor: AiraColors.primary,
        foregroundColor: Colors.white,
        elevation: 0,
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 18),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        side: BorderSide(color: Colors.grey.shade300),
        foregroundColor: AiraColors.navy,
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AiraColors.primary,
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: AiraColors.surfaceMuted,
      side: BorderSide.none,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 0),
      labelStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: AiraColors.surface,
      indicatorColor: AiraColors.primary.withValues(alpha: 0.10),
      labelTextStyle: WidgetStatePropertyAll(
        TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: Colors.grey.shade700,
        ),
      ),
    ),
  );
}
