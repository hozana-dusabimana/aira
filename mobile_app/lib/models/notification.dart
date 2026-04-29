class AppNotification {
  final int id;
  final String title;
  final String? message;
  final String type;
  final int? relatedIncidentId;
  final bool isRead;
  final DateTime createdAt;

  AppNotification({
    required this.id,
    required this.title,
    this.message,
    required this.type,
    this.relatedIncidentId,
    required this.isRead,
    required this.createdAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) => AppNotification(
        id: json['id'] as int,
        title: json['title'] as String,
        message: json['message'] as String?,
        type: json['type'] as String? ?? 'info',
        relatedIncidentId: json['related_incident_id'] as int?,
        isRead: json['is_read'] as bool? ?? false,
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}
