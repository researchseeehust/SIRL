const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

function getNavOffset() {
  const header = $('.site-header');
  const cssValue = getComputedStyle(document.documentElement).getPropertyValue('--nav-height');
  const cssHeight = Number.parseFloat(cssValue) || 0;
  const actualHeight = header?.getBoundingClientRect().height || 0;
  return Math.max(cssHeight, actualHeight);
}

function initNav() {
  const toggle = $('.nav-toggle');
  const links = $('[data-nav-links]');
  toggle?.addEventListener('click', () => {
    const open = links.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(open));
  });

  const navLinks = $$('.nav-links a');
  const progress = $('.scroll-progress span');
  const sections = navLinks.map(a => $(a.getAttribute('href'))).filter(Boolean);

  const onScroll = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    const percent = max > 0 ? (scrollY / max) * 100 : 0;
    if (progress) progress.style.width = `${Math.max(0, Math.min(100, percent))}%`;

    let active = sections[0]?.id;
    const activeOffset = getNavOffset() + 70;
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= activeOffset) active = section.id;
    }
    navLinks.forEach(a => a.classList.toggle('active', a.getAttribute('href') === `#${active}`));
  };
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (!link) return;
    const href = link.getAttribute('href');
    const target = href && href !== '#' ? $(href) : null;
    if (!target) return;
    event.preventDefault();
    const top = target.getBoundingClientRect().top + window.scrollY - getNavOffset();
    window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    history.pushState(null, '', href);
    links?.classList.remove('open');
    toggle?.setAttribute('aria-expanded', 'false');
  });
}

document.addEventListener('DOMContentLoaded', initNav);
