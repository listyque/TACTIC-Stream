// Historical Handler declarations before extraction, 2026-10-15.
// Reference fixture parsed by tab_widths.mjs, not a production component.
readonly property real fittedTabWidth: {
                        const available = searchTabsView.width
                        const naturalTotal = searchTabsView.naturalContentWidth
                        const minimumTotal = searchTabsView.count * minimumTabWidth
                        if (naturalTotal <= available || naturalTotal <= minimumTotal)
                            return naturalTabWidth
                        if (current)
                            return naturalTabWidth
                        const activeWidth = searchTabsView.activeNaturalWidth
                        const inactiveCount = Math.max(0, searchTabsView.count - 1)
                        const inactiveMinimumTotal = inactiveCount * minimumTabWidth
                        const inactiveNaturalTotal = Math.max(
                            inactiveMinimumTotal,
                            naturalTotal - activeWidth
                        )
                        const inactiveAvailable = available - activeWidth
                        if (inactiveAvailable <= inactiveMinimumTotal)
                            return minimumTabWidth
                        const ratio = (inactiveAvailable - inactiveMinimumTotal)
                            / (inactiveNaturalTotal - inactiveMinimumTotal)
                        return minimumTabWidth
                            + (naturalTabWidth - minimumTabWidth) * ratio
                    }
                    property real displacedX: {
                        if (searchTabsView.dragSourceIndex < 0
                                || searchTabsView.dragTargetIndex < 0)
                            return 0
                        if (searchTabsView.dragSourceIndex < searchTabsView.dragTargetIndex
                                && index > searchTabsView.dragSourceIndex
                                && index <= searchTabsView.dragTargetIndex)
                            return -searchTabsView.draggedTabWidth
                        if (searchTabsView.dragSourceIndex > searchTabsView.dragTargetIndex
                                && index >= searchTabsView.dragTargetIndex
                                && index < searchTabsView.dragSourceIndex)
                            return searchTabsView.draggedTabWidth
                        return 0
                    }

                    width: fittedTabWidth
