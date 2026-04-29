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
