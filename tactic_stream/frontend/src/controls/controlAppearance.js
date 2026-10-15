import { buttonVisual } from '../../../src/tactic_stream/shared_ui/core/interaction.mjs';
import { cssRoles } from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';

export function buttonVariables(options) {
  const result = {};
  const states = {
    idle: {},
    hover: { hovered: true },
    focus: { focused: true },
    pressed: { pressed: true },
    disabled: { enabled: false }
  };
  for (const [name, flags] of Object.entries(states)) {
    const paint = buttonVisual({ ...options, ...flags });
    let background =
      paint.background === 'transparent'
        ? 'transparent'
        : `var(${cssRoles[paint.background]})`;
    if (paint.pressedMix)
      background = `color-mix(in srgb, ${background} 82%, var(--page))`;
    result[`--button-${name}-background`] = background;
    result[`--button-${name}-color`] = `var(${cssRoles[paint.content]})`;
    result[`--button-${name}-border`] = `var(${cssRoles[paint.border]})`;
    result[`--button-${name}-border-width`] = paint.borderWidth + 'px';
  }
  return result;
}
