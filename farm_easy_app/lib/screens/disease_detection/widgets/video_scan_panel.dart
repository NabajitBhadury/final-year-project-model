import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../../providers/disease_detection_provider.dart';
import 'media_picker_panel.dart';
import 'video_result_panel.dart';

class VideoScanPanel extends StatelessWidget {
  final DiseaseDetectionProvider provider;

  const VideoScanPanel({super.key, required this.provider});

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('video-mode'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        MediaPickerPanel(
          title: 'Video scan',
          icon: Icons.video_file_outlined,
          fileName: provider.video == null ? null : _fileName(provider.video!),
          preview: provider.video == null
              ? null
              : const Center(
                  child: Icon(Icons.movie_creation_outlined, size: 78),
                ),
          primaryAction: MediaAction(
            icon: Icons.videocam_outlined,
            label: 'Record',
            onPressed: () => provider.pickVideo(ImageSource.camera),
          ),
          secondaryAction: MediaAction(
            icon: Icons.video_library_outlined,
            label: 'Library',
            onPressed: () => provider.pickVideo(ImageSource.gallery),
          ),
        ),
        const SizedBox(height: 14),
        ElevatedButton.icon(
          onPressed: provider.canAnalyzeVideo ? provider.analyzeVideo : null,
          icon: provider.isAnalyzing
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.timeline_outlined),
          label: Text(
            provider.isAnalyzing ? 'Analyzing video' : 'Analyze video',
          ),
        ),
        if (provider.videoResult != null) ...[
          const SizedBox(height: 18),
          VideoResultPanel(result: provider.videoResult!),
        ],
      ],
    );
  }

  String _fileName(File file) {
    return file.path.split(Platform.pathSeparator).last;
  }
}
