// Historical Handler declarations before extraction, 2026-10-15.
// Reference fixture parsed by tab_widths.mjs, not a production component.
property real displacedY: {
                    if (rail.dragSourceIndex < 0 || rail.dragTargetIndex < 0)
                        return 0
                    if (rail.dragSourceIndex < rail.dragTargetIndex
                            && index > rail.dragSourceIndex
                            && index <= rail.dragTargetIndex)
                        return -height - rail.spacing
                    if (rail.dragSourceIndex > rail.dragTargetIndex
                            && index >= rail.dragTargetIndex
                            && index < rail.dragSourceIndex)
                        return height + rail.spacing
                    return 0
                }

                width: revealed ? expandedWidth : root.reservedWidth
