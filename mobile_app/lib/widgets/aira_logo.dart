import 'package:flutter/material.dart';

import '../config/theme.dart';

/// Brand mark for AIRA. A rounded square with a stylised shield + AI dot.
/// Renders without any image asset so it works offline / in fresh checkouts.
class AiraLogo extends StatelessWidget {
  final double size;
  final bool showWordmark;
  final bool dark;
  const AiraLogo({
    super.key,
    this.size = 56,
    this.showWordmark = false,
    this.dark = false,
  });

  @override
  Widget build(BuildContext context) {
    final mark = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AiraColors.accent, AiraColors.primaryDark],
        ),
        borderRadius: BorderRadius.circular(size * 0.24),
        boxShadow: [
          BoxShadow(
            color: AiraColors.primary.withValues(alpha: 0.30),
            blurRadius: size * 0.35,
            offset: Offset(0, size * 0.12),
          ),
        ],
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Icon(
            Icons.shield_outlined,
            color: Colors.white,
            size: size * 0.55,
          ),
          Positioned(
            top: size * 0.18,
            right: size * 0.18,
            child: Container(
              width: size * 0.18,
              height: size * 0.18,
              decoration: BoxDecoration(
                color: AiraColors.success,
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: size * 0.04),
              ),
            ),
          ),
        ],
      ),
    );

    if (!showWordmark) return mark;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        mark,
        SizedBox(width: size * 0.25),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'AIRA',
              style: TextStyle(
                fontSize: size * 0.42,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.8,
                color: dark ? Colors.white : AiraColors.navy,
              ),
            ),
            Text(
              'Rwanda National Police',
              style: TextStyle(
                fontSize: size * 0.20,
                fontWeight: FontWeight.w500,
                color: dark
                    ? Colors.white.withValues(alpha: 0.75)
                    : AiraColors.textMuted,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
