import 'package:flutter/material.dart';
import '../models/user_model.dart';
import '../services/database_service.dart';

class UserProvider extends ChangeNotifier {
  final DatabaseService _dbService = DatabaseService();
  UserModel? _user;
  bool _isLoading = false;

  UserModel? get user => _user;
  bool get isLoading => _isLoading;

  Future<void> loadUser(String uid) async {
    _isLoading = true;
    notifyListeners();

    _user = await _dbService.getUser(uid);

    _isLoading = false;
    notifyListeners();
  }

  Future<bool> updateProfile({
    required String name,
    String? phone,
    String? location,
    String? farmSize,
    List<String>? crops,
  }) async {
    if (_user == null) return false;

    _isLoading = true;
    notifyListeners();

    try {
      final updatedUser = _user!.copyWith(
        name: name,
        phone: phone,
        location: location,
        farmSize: farmSize,
        mainCrops: crops,
      );

      await _dbService.updateUser(updatedUser);
      _user = updatedUser;

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  void clearUser() {
    _user = null;
    notifyListeners();
  }
}
