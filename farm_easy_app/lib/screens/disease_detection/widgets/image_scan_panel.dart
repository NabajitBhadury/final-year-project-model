import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../../providers/disease_detection_provider.dart';
import 'media_picker_panel.dart';
import 'prediction_result_panel.dart';

class ImageScanPanel extends StatelessWidget {
  final DiseaseDetectionProvider provider;

  const ImageScanPanel({super.key, required this.provider});

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('image-mode'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        MediaPickerPanel(
          title: 'Image scan',
          icon: Icons.add_a_photo_rounded,
          fileName: provider.image == null ? null : _fileName(provider.image!),
          preview: provider.image == null
              ? null
              : Image.file(
                  provider.image!,
                  width: double.infinity,
                  fit: BoxFit.cover,
                ),
          primaryAction: MediaAction(
            icon: Icons.camera_alt_outlined,
            label: 'Camera',
            onPressed: () => provider.pickImage(ImageSource.camera),
          ),
          secondaryAction: MediaAction(
            icon: Icons.photo_library_outlined,
            label: 'Gallery',
            onPressed: () => provider.pickImage(ImageSource.gallery),
          ),
        ),
        const SizedBox(height: 14),
        ElevatedButton.icon(
          onPressed: provider.canAnalyzeImage ? provider.analyzeImage : null,
          icon: provider.isAnalyzing
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.analytics_outlined),
          label: Text(
            provider.isAnalyzing ? 'Analyzing image' : 'Analyze image',
          ),
        ),
        if (provider.imageResult != null) ...[
          const SizedBox(height: 18),
          PredictionResultPanel(result: provider.imageResult!),
        ],
      ],
    );
  }

  String _fileName(File file) {
    return file.path.split(Platform.pathSeparator).last;
  }
}
