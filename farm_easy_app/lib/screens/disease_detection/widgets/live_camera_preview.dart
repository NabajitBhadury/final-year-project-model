import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

class LiveCameraPreview extends StatelessWidget {
  final CameraController? controller;

  const LiveCameraPreview({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    final activeController = controller;
    final colorScheme = Theme.of(context).colorScheme;
    if (activeController == null || !activeController.value.isInitialized) {
      return Container(
        height: 360,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(18),
        ),
        child: const Icon(Icons.no_photography_outlined, size: 52),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: AspectRatio(
        aspectRatio: activeController.value.aspectRatio,
        child: CameraPreview(activeController),
      ),
    );
  }
}
