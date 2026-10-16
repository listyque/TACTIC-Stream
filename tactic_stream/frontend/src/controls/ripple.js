// Handler MaterialRipple: the press origin, 2.2× diameter and independent fade.
export function ripple(event) {
  const button = event.currentTarget;
  if (button.disabled || event.button !== 0) return;
  const style = getComputedStyle(button);
  const fast = parseFloat(style.getPropertyValue('--motion-click')) || 0;
  const extended =
    parseFloat(style.getPropertyValue('--motion-click-extended')) || 0;
  if (!extended) return;
  button
    .querySelectorAll(':scope > .control-ripple-clip')
    .forEach((node) => node.remove());
  const inset = parseFloat(style.getPropertyValue('--ripple-inset')) || 0;
  const bounds = button.getBoundingClientRect(),
    diameter =
      Math.max(bounds.width - inset * 2, bounds.height - inset * 2) * 2.2;
  const circle = document.createElement('span');
  circle.className = 'control-ripple';
  circle.setAttribute('aria-hidden', 'true');
  Object.assign(circle.style, {
    width: diameter + 'px',
    height: diameter + 'px',
    left: event.clientX - bounds.left - inset - diameter / 2 + 'px',
    top: event.clientY - bounds.top - inset - diameter / 2 + 'px'
  });
  const clip = document.createElement('span');
  clip.className = 'control-ripple-clip';
  clip.setAttribute('aria-hidden', 'true');
  clip.style.inset = inset + 'px';
  clip.append(circle);
  button.append(clip);
  circle.animate([{ transform: 'scale(.05)' }, { transform: 'scale(1)' }], {
    duration: extended + fast,
    easing: 'cubic-bezier(.215,.61,.355,1)',
    fill: 'forwards'
  });
  const fade = circle.animate([{ opacity: 0.42 }, { opacity: 0 }], {
    duration: extended,
    delay: 24,
    easing: 'ease-out',
    fill: 'forwards'
  });
  fade.finished.then(
    () => clip.remove(),
    () => clip.remove()
  );
}
