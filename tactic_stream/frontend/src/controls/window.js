import { h, render } from 'vue';
import WindowControls from './WindowControls.vue';
import './dialog.css';
let activeWindow = null;

// Dialogs block their owner; utility windows keep the workspace available.
export const windowDirective = {
  mounted(element, binding) {
    if (element.tagName !== 'DIALOG') return;
    let configuration = binding.value;
    let header = null,
      host = null,
      retainedGeometry = null,
      hostedGeometry = null;
    let chrome = null,
      frameContent = null,
      contentClose = null,
      contentHelp = null;
    const show = element.show.bind(element),
      close = element.close.bind(element);
    const home = document.createComment('window owner');
    element.before(home);
    let owner = null,
      returnFocus = null;
    const nonmodal = () => ['window', 'popup'].includes(configuration?.type);
    function closed() {
      if (element.matches(':popover-open')) element.hidePopover();
      owner?.removeEventListener('close', closeChild);
      owner = null;
      if (
        home.parentNode &&
        (element.parentNode !== home.parentNode ||
          element.previousSibling !== home)
      )
        home.after(element);
      if (activeWindow === element) activeWindow = null;
    }
    function nativeClosed() {
      if (element.open) return;
      closed();
      if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
      returnFocus = null;
    }
    function closeChild(event) {
      if (event.target === owner) element.close();
    }
    function raise(event) {
      if (
        !element.open ||
        !element.matches(':popover-open') ||
        activeWindow === element ||
        element.querySelector('dialog:modal')
      )
        return;
      if (event && event.target.closest('[popover]') !== element) return;
      const focused = element.contains(document.activeElement)
        ? document.activeElement
        : null;
      element.hidePopover();
      element.showPopover();
      focused?.focus({ preventScroll: true });
      activeWindow = element;
    }
    element.show = () => {
      if (!nonmodal()) {
        if (element.matches(':modal')) element.focus();
        else show();
        return;
      }
      if (element.open) {
        element.dispatchEvent(new Event('windowshow'));
        raise();
        return;
      }
      returnFocus = document.activeElement;
      owner =
        returnFocus?.closest(
          configuration.type === 'popup' ? 'dialog[open]' : 'dialog:modal'
        ) ||
        [...document.querySelectorAll('dialog:modal')].at(-1) ||
        null;
      if (owner === element || element.contains(owner)) owner = null;
      if (owner) {
        owner.append(element);
        owner.addEventListener('close', closeChild);
      }
      element.popover = 'manual';
      show();
      element.showPopover();
      activeWindow = element;
      element.dispatchEvent(new Event('windowshow'));
    };
    element.close = (...args) => {
      closed();
      close(...args);
      if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
      returnFocus = null;
    };
    function escape(event) {
      if (
        event.key !== 'Escape' ||
        event.defaultPrevented ||
        !nonmodal() ||
        event.target.closest('dialog') !== element
      )
        return;
      event.preventDefault();
      event.stopPropagation();
      if (element.dispatchEvent(new Event('cancel', { cancelable: true })))
        element.close();
    }
    function rememberGeometry(event) {
      if (event.target !== element || !element.open) return;
      const { x, y, width, height, maximized, restore } = event.detail;
      retainedGeometry = { rect: { x, y, width, height }, maximized, restore };
    }
    element.addEventListener('windowgeometrychange', rememberGeometry);
    element.addEventListener('keydown', escape);
    element.addEventListener('close', nativeClosed);
    element.addEventListener('pointerdown', raise);
    function placeControls() {
      const last = [...header.querySelectorAll('button')].at(-1);
      const anchor =
        last?.parentElement.tagName === 'FORM' ? last.parentElement : last;
      if (anchor) anchor.before(host);
      else header.append(host);
    }
    const attach = () => {
      const windowed =
        configuration !== false && configuration?.type !== 'popup';
      element.classList.toggle('app-window', windowed);
      element.dataset.windowType = configuration?.type || 'dialog';
      element.dataset.windowKind = configuration?.kind || '';
      if (nonmodal()) element.setAttribute('aria-modal', 'false');
      else element.removeAttribute('aria-modal');
      const featureHeader = !windowed
        ? null
        : [
            ...element.querySelectorAll('header:not([data-window-chrome])')
          ].find((header) => header.closest('dialog') === element) || null;
      const frameView = [...element.querySelectorAll('.frame-view')].find(
        (view) => view.closest('dialog') === element
      );
      const frameHeader =
        windowed &&
        (featureHeader?.classList.contains('frame-titlebar') ||
          (!featureHeader &&
            !!frameView &&
            (frameView.parentElement === element ||
              (frameView.parentElement?.parentElement === element &&
                frameView.parentElement.matches(
                  '.frame-host, .frame-host-body'
                )))));
      if (frameHeader && !chrome) {
        chrome = document.createElement('header');
        chrome.dataset.windowChrome = '';
        chrome.className = 'app-dialog-titlebar';
        element.prepend(chrome);
        element.classList.add('app-window-frame-host');
      } else if (!frameHeader && chrome) {
        chrome.remove();
        chrome = null;
        frameContent?.classList.remove('app-window-frame-content');
        frameContent = null;
        element.classList.remove('app-window-frame-host');
      }
      if (frameHeader) {
        let content = featureHeader || frameView;
        while (content.parentElement !== element)
          content = content.parentElement;
        if (frameContent !== content) {
          frameContent?.classList.remove('app-window-frame-content');
          frameContent = content;
          frameContent.classList.add('app-window-frame-content');
        }
      }
      const closeButton = featureHeader
        ? [...featureHeader.querySelectorAll('button')].find(
            (button) =>
              !button.closest('.app-window-controls') &&
              button.querySelector(
                '[data-icon="close"], [data-icon="MDI_CLOSE"]'
              )
          )
        : null;
      const hiddenClose = frameHeader ? closeButton : null;
      if (contentClose !== hiddenClose) {
        contentClose?.classList.remove('app-window-content-close');
        contentClose = hiddenClose;
        contentClose?.classList.add('app-window-content-close');
      }
      const helpButton =
        frameHeader && featureHeader
          ? [...featureHeader.querySelectorAll('button')].find(
              (button) =>
                !button.closest('.app-window-controls') &&
                button.querySelector(
                  '[data-icon="help"], [data-icon="MDI_HELP_CIRCLE"]'
                )
            )
          : null;
      if (contentHelp !== helpButton) {
        contentHelp?.classList.remove('app-window-content-help');
        contentHelp = helpButton;
        contentHelp?.classList.add('app-window-content-help');
      }
      const next = chrome || featureHeader;
      const properties = () => ({
        element,
        header,
        geometry: hostedGeometry,
        backProvided: !!configuration?.backProvided,
        title: chrome
          ? element.getAttribute('aria-label') || element.dataset.windowKind
          : '',
        closeButton: contentClose,
        closeRequired: !!chrome || !closeButton,
        closeDisabled: !!contentClose?.disabled,
        helpButton: contentHelp,
        helpLabel: contentHelp?.getAttribute('aria-label') || '',
        helpDisabled: !!contentHelp?.disabled
      });
      if (next === header) {
        if (host && !header.contains(host)) placeControls();
        if (host) render(h(WindowControls, properties()), host);
        return;
      }
      if (host) {
        render(null, host);
        host.remove();
      }
      header = next;
      host = null;
      if (!header) return;
      hostedGeometry = configuration?.geometry || retainedGeometry;
      host = document.createElement('span');
      host.className = 'app-window-controls';
      placeControls();
      render(h(WindowControls, properties()), host);
    };
    const observer = new MutationObserver(attach);
    observer.observe(element, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['aria-label', 'disabled']
    });
    attach();
    element.windowConfigure = (value) => {
      if (value?.geometry) hostedGeometry = value.geometry;
      configuration = value;
      attach();
    };
    element.windowCleanup = () => {
      closed();
      home.remove();
      element.show = show;
      element.close = close;
      element.removeEventListener('windowgeometrychange', rememberGeometry);
      element.removeEventListener('keydown', escape);
      element.removeEventListener('close', nativeClosed);
      element.removeEventListener('pointerdown', raise);
      observer.disconnect();
      if (host) {
        render(null, host);
        host.remove();
      }
      chrome?.remove();
      frameContent?.classList.remove('app-window-frame-content');
      contentClose?.classList.remove('app-window-content-close');
      contentHelp?.classList.remove('app-window-content-help');
      element.classList.remove('app-window-frame-host');
    };
  },
  updated(element, binding) {
    element.windowConfigure?.(binding.value);
  },
  beforeUnmount(element) {
    element.windowCleanup?.();
    element.classList.remove('app-window');
    delete element.windowCleanup;
    delete element.windowConfigure;
  }
};
