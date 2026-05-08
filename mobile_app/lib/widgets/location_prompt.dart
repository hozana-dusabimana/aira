import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import '../config/theme.dart';

/// Why location is currently unavailable.
enum LocationIssue { serviceOff, permissionDenied, permissionDeniedForever, ok }

class LocationStatus {
  final LocationIssue issue;
  final Position? position;
  const LocationStatus({required this.issue, this.position});

  bool get isOk => issue == LocationIssue.ok;
}

/// Resolves the current location status without ever throwing.
Future<LocationStatus> resolveLocationStatus({bool fetch = true}) async {
  try {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      return const LocationStatus(issue: LocationIssue.serviceOff);
    }
    LocationPermission p = await Geolocator.checkPermission();
    if (p == LocationPermission.denied) {
      p = await Geolocator.requestPermission();
    }
    if (p == LocationPermission.denied) {
      return const LocationStatus(issue: LocationIssue.permissionDenied);
    }
    if (p == LocationPermission.deniedForever) {
      return const LocationStatus(issue: LocationIssue.permissionDeniedForever);
    }
    if (!fetch) {
      return const LocationStatus(issue: LocationIssue.ok);
    }
    final pos = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 12),
      ),
    );
    return LocationStatus(issue: LocationIssue.ok, position: pos);
  } catch (_) {
    return const LocationStatus(issue: LocationIssue.serviceOff);
  }
}

/// Banner shown when location services / permissions are not available, with
/// a CTA to either turn on location services or open app settings.
class LocationDisabledBanner extends StatelessWidget {
  final LocationIssue issue;
  final VoidCallback onResolved;
  const LocationDisabledBanner({
    super.key,
    required this.issue,
    required this.onResolved,
  });

  String get _title {
    switch (issue) {
      case LocationIssue.serviceOff:
        return 'Location is turned off';
      case LocationIssue.permissionDenied:
        return 'Location permission needed';
      case LocationIssue.permissionDeniedForever:
        return 'Location is blocked';
      case LocationIssue.ok:
        return '';
    }
  }

  String get _body {
    switch (issue) {
      case LocationIssue.serviceOff:
        return 'Turn on your phone’s location so police can be sent to the exact incident scene.';
      case LocationIssue.permissionDenied:
        return 'AIRA needs your location to attach an accurate place to this report.';
      case LocationIssue.permissionDeniedForever:
        return 'You blocked location for AIRA. Open app settings to allow it again.';
      case LocationIssue.ok:
        return '';
    }
  }

  String get _ctaLabel {
    switch (issue) {
      case LocationIssue.serviceOff:
        return 'Turn on location';
      case LocationIssue.permissionDenied:
        return 'Allow location';
      case LocationIssue.permissionDeniedForever:
        return 'Open app settings';
      case LocationIssue.ok:
        return '';
    }
  }

  Future<void> _handleCta() async {
    if (issue == LocationIssue.serviceOff) {
      await Geolocator.openLocationSettings();
    } else if (issue == LocationIssue.permissionDeniedForever) {
      await Geolocator.openAppSettings();
    } else {
      // Re-trigger the OS prompt
      await Geolocator.requestPermission();
    }
    // Caller decides when/how to re-check after the user returns.
    onResolved();
  }

  @override
  Widget build(BuildContext context) {
    if (issue == LocationIssue.ok) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AiraColors.warning.withValues(alpha: 0.10),
        border: Border.all(color: AiraColors.warning.withValues(alpha: 0.45)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AiraColors.warning.withValues(alpha: 0.20),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.location_off,
                color: AiraColors.warning, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _title,
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    color: AiraColors.navy,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _body,
                  style: TextStyle(
                    color: Colors.grey.shade700,
                    fontSize: 13,
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: 10),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AiraColors.warning,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  icon: const Icon(Icons.location_on, size: 18),
                  label: Text(_ctaLabel),
                  onPressed: _handleCta,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
