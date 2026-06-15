import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class LiveConnectionPanel extends StatelessWidget {
  final bool isLive;
  final Uri liveUri;

  const LiveConnectionPanel({
    super.key,
    required this.isLive,
    required this.liveUri,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colorScheme.outlineVariant),
      ),
      child: Row(
        children: [
          Icon(
            isLive ? Icons.sensors : Icons.sensors_off_outlined,
            color: isLive ? Colors.green : colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              isLive
                  ? 'Live stream connected'
                  : 'Ready to connect to ${liveUri.host}',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: GoogleFonts.outfit(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
