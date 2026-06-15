import 'package:flutter/material.dart';

import '../../../providers/disease_detection_provider.dart';

class ScanModeSelector extends StatelessWidget {
  final ScanMode mode;
  final ValueChanged<ScanMode> onChanged;

  const ScanModeSelector({
    super.key,
    required this.mode,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return SegmentedButton<ScanMode>(
      segments: const [
        ButtonSegment(
          value: ScanMode.image,
          icon: Icon(Icons.photo_camera_outlined),
          label: Text('Image'),
        ),
        ButtonSegment(
          value: ScanMode.video,
          icon: Icon(Icons.videocam_outlined),
          label: Text('Video'),
        ),
        ButtonSegment(
          value: ScanMode.live,
          icon: Icon(Icons.sensors_outlined),
          label: Text('Live'),
        ),
      ],
      selected: {mode},
      onSelectionChanged: (value) => onChanged(value.first),
      showSelectedIcon: false,
    );
  }
}
