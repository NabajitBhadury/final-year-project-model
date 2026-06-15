import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../../providers/disease_detection_provider.dart';
import 'live_detection_screen.dart';
import 'widgets/detection_header.dart';
import 'widgets/image_scan_panel.dart';
import 'widgets/live_entry_card.dart';
import 'widgets/scan_mode_selector.dart';
import 'widgets/status_panels.dart';
import 'widgets/video_scan_panel.dart';

class UploadScreen extends StatelessWidget {
  const UploadScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => DiseaseDetectionProvider(),
      child: const _UploadView(),
    );
  }
}

class _UploadView extends StatelessWidget {
  const _UploadView();

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final provider = context.watch<DiseaseDetectionProvider>();

    return Scaffold(
      backgroundColor: colorScheme.surface,
      appBar: AppBar(
        title: Text(
          'Crop Health Scan',
          style: GoogleFonts.outfit(fontWeight: FontWeight.w700),
        ),
        centerTitle: true,
        backgroundColor: colorScheme.surface,
        elevation: 0,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const DetectionHeader().animate().fadeIn().slideY(begin: 0.1),
              const SizedBox(height: 16),
              ScanModeSelector(
                mode: provider.mode,
                onChanged: provider.selectMode,
              ).animate().fadeIn(delay: 120.ms),
              const SizedBox(height: 18),
              AnimatedSwitcher(
                duration: 250.ms,
                child: switch (provider.mode) {
                  ScanMode.image => ImageScanPanel(provider: provider),
                  ScanMode.video => VideoScanPanel(provider: provider),
                  ScanMode.live => LiveEntryCard(
                    onOpen: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const LiveDetectionScreen(),
                      ),
                    ),
                  ),
                },
              ),
              if (provider.error != null) ...[
                const SizedBox(height: 16),
                ErrorPanel(message: provider.error!),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
