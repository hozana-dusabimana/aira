class User {
  final int id;
  final String fullName;
  final String? email;
  final String? phone;
  final String role;
  final bool isVerified;

  User({
    required this.id,
    required this.fullName,
    this.email,
    this.phone,
    required this.role,
    required this.isVerified,
  });

  factory User.fromJson(Map<String, dynamic> json) => User(
        id: json['id'] as int,
        fullName: json['full_name'] as String,
        email: json['email'] as String?,
        phone: json['phone'] as String?,
        role: json['role'] as String,
        isVerified: json['is_verified'] as bool? ?? false,
      );
}
