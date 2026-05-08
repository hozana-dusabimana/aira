import 'package:flutter/material.dart';

import '../config/theme.dart';

/// Pill chip used in headers to show an incident's lifecycle status.
class StatusChip extends StatelessWidget {
  final String status;
  final bool dense;
  const StatusChip({super.key, required this.status, this.dense = false});

  @override
  Widget build(BuildContext context) {
    final c = statusColor(status);
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: dense ? 8 : 10,
        vertical: dense ? 3 : 4,
      ),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        status.replaceAll('_', ' ').toUpperCase(),
        style: TextStyle(
          color: c,
          fontWeight: FontWeight.w700,
          fontSize: dense ? 10 : 11,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}

/// Pill chip for severity (low / medium / high / critical).
class SeverityChip extends StatelessWidget {
  final String severity;
  final bool dense;
  const SeverityChip({super.key, required this.severity, this.dense = false});

  @override
  Widget build(BuildContext context) {
    final c = severityColor(severity);
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: dense ? 8 : 10,
        vertical: dense ? 3 : 4,
      ),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(color: c, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          Text(
            severity.toUpperCase(),
            style: TextStyle(
              color: c,
              fontWeight: FontWeight.w700,
              fontSize: dense ? 10 : 11,
              letterSpacing: 0.4,
            ),
          ),
        ],
      ),
    );
  }
}
