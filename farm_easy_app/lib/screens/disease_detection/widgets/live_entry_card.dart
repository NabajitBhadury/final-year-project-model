import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class LiveEntryCard extends StatelessWidget {
  final VoidCallback onOpen;

  const LiveEntryCard({super.key, required this.onOpen});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      key: const ValueKey('live-mode'),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Icon(Icons.center_focus_strong, size: 54, color: colorScheme.primary),
          const SizedBox(height: 14),
          Text(
            'Live detection',
            textAlign: TextAlign.center,
            style: GoogleFonts.outfit(
              fontSize: 22,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Send camera frames to the backend and watch the latest leaf result update.',
            textAlign: TextAlign.center,
            style: TextStyle(color: colorScheme.onSurfaceVariant, height: 1.3),
          ),
          const SizedBox(height: 18),
          ElevatedButton.icon(
            onPressed: onOpen,
            icon: const Icon(Icons.play_arrow_rounded),
            label: const Text('Open live detection'),
          ),
        ],
      ),
    );
  }
}
