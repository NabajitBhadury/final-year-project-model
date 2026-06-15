import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class MediaAction {
  final IconData icon;
  final String label;
  final VoidCallback onPressed;

  const MediaAction({
    required this.icon,
    required this.label,
    required this.onPressed,
  });
}

class MediaPickerPanel extends StatelessWidget {
  final String title;
  final IconData icon;
  final String? fileName;
  final Widget? preview;
  final MediaAction primaryAction;
  final MediaAction secondaryAction;

  const MediaPickerPanel({
    super.key,
    required this.title,
    required this.icon,
    required this.fileName,
    required this.preview,
    required this.primaryAction,
    required this.secondaryAction,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(icon, color: colorScheme.primary),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  title,
                  style: GoogleFonts.outfit(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: Container(
              height: 245,
              width: double.infinity,
              color: colorScheme.surfaceContainerHigh,
              child:
                  preview ??
                  Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(icon, size: 56, color: colorScheme.primary),
                      const SizedBox(height: 10),
                      Text(
                        'No file selected',
                        style: TextStyle(color: colorScheme.onSurfaceVariant),
                      ),
                    ],
                  ),
            ),
          ),
          if (fileName != null) ...[
            const SizedBox(height: 10),
            Text(
              fileName!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(color: colorScheme.onSurfaceVariant),
            ),
          ],
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(child: _PickerButton(action: primaryAction)),
              const SizedBox(width: 10),
              Expanded(child: _PickerButton(action: secondaryAction)),
            ],
          ),
        ],
      ),
    );
  }
}

class _PickerButton extends StatelessWidget {
  final MediaAction action;

  const _PickerButton({required this.action});

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: action.onPressed,
      icon: Icon(action.icon),
      label: Text(action.label, overflow: TextOverflow.ellipsis),
    );
  }
}
