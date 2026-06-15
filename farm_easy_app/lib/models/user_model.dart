import 'package:cloud_firestore/cloud_firestore.dart';

class UserModel {
  final String uid;
  final String email;
  final String name;
  final String? phone;
  final String? location;
  final String? farmSize;
  final List<String>? mainCrops;
  final String? profileImageUrl;
  final DateTime createdAt;

  UserModel({
    required this.uid,
    required this.email,
    required this.name,
    this.phone,
    this.location,
    this.farmSize,
    this.mainCrops,
    this.profileImageUrl,
    required this.createdAt,
  });

  factory UserModel.fromMap(Map<String, dynamic> map, String id) {
    return UserModel(
      uid: id,
      email: map['email'] ?? '',
      name: map['name'] ?? 'Unknown User',
      phone: map['phone'],
      location: map['location'],
      farmSize: map['farmSize'],
      mainCrops: map['mainCrops'] != null
          ? List<String>.from(map['mainCrops'])
          : null,
      profileImageUrl: map['profileImageUrl'],
      createdAt: (map['createdAt'] as Timestamp?)?.toDate() ?? DateTime.now(),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'uid': uid,
      'email': email,
      'name': name,
      'phone': phone,
      'location': location,
      'farmSize': farmSize,
      'mainCrops': mainCrops,
      'profileImageUrl': profileImageUrl,
    };
  }

  UserModel copyWith({
    String? name,
    String? phone,
    String? location,
    String? farmSize,
    List<String>? mainCrops,
    String? profileImageUrl,
  }) {
    return UserModel(
      uid: uid,
      email: email,
      name: name ?? this.name,
      phone: phone ?? this.phone,
      location: location ?? this.location,
      farmSize: farmSize ?? this.farmSize,
      mainCrops: mainCrops ?? this.mainCrops,
      profileImageUrl: profileImageUrl ?? this.profileImageUrl,
      createdAt: createdAt,
    );
  }
}
