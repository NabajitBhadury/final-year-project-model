import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:image_picker/image_picker.dart';

import '../models/disease_prediction_model.dart';
import '../services/farmeasy_api_service.dart';

enum ScanMode { image, video, live }

class DiseaseDetectionProvider extends ChangeNotifier {
  DiseaseDetectionProvider({
    ImagePicker? picker,
    FarmEasyApiService? apiService,
  }) : _picker = picker ?? ImagePicker(),
       _api = apiService ?? FarmEasyApiService();

  final ImagePicker _picker;
  final FarmEasyApiService _api;

  ScanMode _mode = ScanMode.image;
  File? _image;
  File? _video;
  DiseasePrediction? _imageResult;
  VideoPredictionResult? _videoResult;
  bool _isAnalyzing = false;
  String? _error;

  ScanMode get mode => _mode;
  File? get image => _image;
  File? get video => _video;
  DiseasePrediction? get imageResult => _imageResult;
  VideoPredictionResult? get videoResult => _videoResult;
  bool get isAnalyzing => _isAnalyzing;
  String? get error => _error;

  bool get canAnalyzeImage => _image != null && !_isAnalyzing;
  bool get canAnalyzeVideo => _video != null && !_isAnalyzing;

  void selectMode(ScanMode mode) {
    _mode = mode;
    _error = null;
    notifyListeners();
  }

  Future<void> pickImage(ImageSource source) async {
    final pickedFile = await _picker.pickImage(
      source: source,
      imageQuality: 88,
      maxWidth: 1600,
    );
    if (pickedFile == null) return;
    _image = File(pickedFile.path);
    _imageResult = null;
    _error = null;
    notifyListeners();
  }

  Future<void> pickVideo(ImageSource source) async {
    final pickedFile = await _picker.pickVideo(
      source: source,
      maxDuration: const Duration(minutes: 2),
    );
    if (pickedFile == null) return;
    _video = File(pickedFile.path);
    _videoResult = null;
    _error = null;
    notifyListeners();
  }

  Future<void> analyzeImage() async {
    if (!canAnalyzeImage) return;
    _setBusy(true);
    try {
      _imageResult = await _api.predictImage(_image!);
      _error = null;
    } catch (error) {
      _error = error.toString();
    } finally {
      _setBusy(false);
    }
  }

  Future<void> analyzeVideo() async {
    if (!canAnalyzeVideo) return;
    _setBusy(true);
    try {
      _videoResult = await _api.predictVideo(_video!);
      _error = null;
    } catch (error) {
      _error = error.toString();
    } finally {
      _setBusy(false);
    }
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  void _setBusy(bool value) {
    _isAnalyzing = value;
    if (value) _error = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _api.dispose();
    super.dispose();
  }
}
