import './tooltip.css';
import { controls } from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';

// Handler ToolTip.qml: 500 ms delay, 5 s timeout, inverse theme and viewport placement.
let active,
  sequence = 0;
export const tooltipDirective = {
  mounted(element, binding) {
    let text = binding.value,
      timer,
      timeout,
      popup,
      describedBy;
    function close(event) {
      if (popup && event?.type === 'keydown' && event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
      }
      clearTimeout(timer);
      clearTimeout(timeout);
      if (popup) {
        const dismissed = popup;
        dismissed.hidePopover();
        setTimeout(
          () => dismissed.remove(),
          parseFloat(getComputedStyle(dismissed).transitionDuration) * 1000 + 10
        );
        popup = null;
        if (describedBy === null) element.removeAttribute('aria-describedby');
        else element.setAttribute('aria-describedby', describedBy);
      }
      for (const name of [
        'scroll',
        'resize',
        'pointerdown',
        'keydown',
        'close'
      ])
        window.removeEventListener(name, close, true);
      if (active === close) active = null;
    }
    function start(event) {
      if (
        !text ||
        element.disabled ||
        element.getAttribute('aria-disabled') === 'true' ||
        event.pointerType === 'touch'
      )
        return;
      active?.();
      active = close;
      for (const name of [
        'scroll',
        'resize',
        'pointerdown',
        'keydown',
        'close'
      ])
        window.addEventListener(name, close, true);
      timer = setTimeout(() => {
        if (
          !element.isConnected ||
          element.disabled ||
          element.getAttribute('aria-disabled') === 'true' ||
          !element.getClientRects().length
        ) {
          close();
          return;
        }
        popup = document.createElement('div');
        popup.className = 'app-tooltip';
        popup.popover = 'manual';
        popup.id = 'app-tooltip-' + ++sequence;
        popup.role = 'tooltip';
        popup.textContent = text;
        // A tooltip inside a modal must belong to that modal to avoid inertness.
        (element.closest('dialog') || document.body).append(popup);
        popup.showPopover();
        const anchor = element.getBoundingClientRect(),
          box = popup.getBoundingClientRect(),
          margin = controls.tooltip.margin;
        popup.style.left =
          Math.max(
            margin,
            Math.min(
              innerWidth - box.width - margin,
              anchor.left + (anchor.width - box.width) / 2
            )
          ) + 'px';
        popup.style.top =
          Math.max(
            margin,
            Math.min(
              innerHeight - box.height - margin,
              anchor.bottom + box.height + 2 * margin > innerHeight
                ? anchor.top - box.height - margin
                : anchor.bottom + margin
            )
          ) + 'px';
        describedBy = element.getAttribute('aria-describedby');
        element.setAttribute(
          'aria-describedby',
          [describedBy, popup.id].filter(Boolean).join(' ')
        );
        timeout = setTimeout(close, controls.tooltip.timeout);
      }, controls.tooltip.delay);
    }
    element.addEventListener('pointerenter', start);
    element.addEventListener('focusin', start);
    element.addEventListener('pointerleave', close);
    element.addEventListener('focusout', close);
    element.tooltipUpdate = (value) => {
      text = value;
      close();
    };
    element.tooltipCleanup = () => {
      close();
      element.removeEventListener('pointerenter', start);
      element.removeEventListener('focusin', start);
      element.removeEventListener('pointerleave', close);
      element.removeEventListener('focusout', close);
    };
  },
  updated(element, binding) {
    if (binding.value !== binding.oldValue)
      element.tooltipUpdate?.(binding.value);
  },
  // Teleported window controls can be removed again during a responsive host update.
  beforeUnmount(element) {
    element.tooltipCleanup?.();
    delete element.tooltipUpdate;
    delete element.tooltipCleanup;
  }
};
