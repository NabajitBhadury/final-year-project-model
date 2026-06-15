import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../../providers/live_detection_provider.dart';
import 'widgets/live_camera_preview.dart';
import 'widgets/live_connection_panel.dart';
import 'widgets/live_controls.dart';
import 'widgets/live_result_panel.dart';
import 'widgets/status_panels.dart';

class LiveDetectionScreen extends StatelessWidget {
  const LiveDetectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => LiveDetectionProvider()..initializeCamera(),
      child: const _LiveDetectionView(),
    );
  }
}

class _LiveDetectionView extends StatelessWidget {
  const _LiveDetectionView();

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<LiveDetectionProvider>();
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: colorScheme.surface,
      appBar: AppBar(
        title: Text(
          'Live Detection',
          style: GoogleFonts.outfit(fontWeight: FontWeight.w700),
        ),
        backgroundColor: colorScheme.surface,
      ),
      body: SafeArea(
        child: provider.isInitializing
            ? const Center(child: CircularProgressIndicator())
            : SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    LiveCameraPreview(controller: provider.cameraController),
                    const SizedBox(height: 14),
                    LiveControls(
                      isLive: provider.isLive,
                      onStart: provider.startLive,
                      onStop: provider.stopLive,
                    ),
                    const SizedBox(height: 14),
                    LiveConnectionPanel(
                      isLive: provider.isLive,
                      liveUri: provider.liveUri,
                    ),
                    if (provider.latestPrediction != null) ...[
                      const SizedBox(height: 14),
                      LiveResultPanel(result: provider.latestPrediction!),
                    ],
                    if (provider.error != null) ...[
                      const SizedBox(height: 14),
                      ErrorPanel(message: provider.error!),
                    ],
                  ],
                ),
              ),
      ),
    );
  }
}
