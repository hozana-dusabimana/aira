class Incident {
  final int id;
  final int reporterId;
  final String? imageUrl;
  final String? aiDescription;
  final String? userDescription;
  final String? incidentType;
  final String severityLevel;
  final double? latitude;
  final double? longitude;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? resolvedAt;

  Incident({
    required this.id,
    required this.reporterId,
    this.imageUrl,
    this.aiDescription,
    this.userDescription,
    this.incidentType,
    required this.severityLevel,
    this.latitude,
    this.longitude,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.resolvedAt,
  });

  /// Human-friendly label for [incidentType]. Falls back gracefully so the
  /// user never sees a raw "unknown" / null value.
  String get typeLabel {
    const labels = {
      'fire': 'Fire',
      'traffic': 'Traffic accident',
      'violent_crime': 'Violent crime',
      'theft': 'Theft',
      'vandalism': 'Vandalism',
      'suspicious_activity': 'Suspicious activity',
      'general': 'Other',
    };
    final t = incidentType?.trim().toLowerCase();
    if (t == null || t.isEmpty) return 'Pending review';
    final mapped = labels[t];
    if (mapped != null) return mapped;
    final pretty = t.replaceAll('_', ' ');
    return pretty[0].toUpperCase() + pretty.substring(1);
  }

  factory Incident.fromJson(Map<String, dynamic> json) => Incident(
        id: json['id'] as int,
        reporterId: json['reporter_id'] as int,
        imageUrl: json['image_url'] as String?,
        aiDescription: json['ai_description'] as String?,
        userDescription: json['user_description'] as String?,
        incidentType: json['incident_type'] as String?,
        severityLevel: json['severity_level'] as String? ?? 'medium',
        latitude: (json['latitude'] as num?)?.toDouble(),
        longitude: (json['longitude'] as num?)?.toDouble(),
        status: json['status'] as String? ?? 'pending',
        createdAt: DateTime.parse(json['created_at'] as String),
        updatedAt: DateTime.parse(json['updated_at'] as String),
        resolvedAt: json['resolved_at'] != null
            ? DateTime.parse(json['resolved_at'] as String)
            : null,
      );
}
