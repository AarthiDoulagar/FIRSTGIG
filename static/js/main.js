/**
 * FirstGig Client-Side Logic
 * - Dual Custom Cursor (Desktop only, gold dot + trailing glow)
 * - Homepage opening logo animation
 * - Mobile Navigation Drawer
 * - Demo Quick Switcher Dropdown
 * - Timeline switching
 */

document.addEventListener('DOMContentLoaded', () => {
  initCustomCursor();
  initOpeningAnimation();
  initMobileNav();
  initDemoSwitcher();
  initTimelineToggle();
  initFlashDismiss();
});

/* ==========================================================================
   CUSTOM CURSOR (DESKTOP ONLY)
   ========================================================================== */
function initCustomCursor() {
  const isTouch = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || (window.innerWidth <= 768);
  if (isTouch) return;

  const dot = document.querySelector('.cursor-dot');
  const glow = document.querySelector('.cursor-glow');
  if (!dot || !glow) return;

  document.body.classList.add('has-custom-cursor');

  let mouseX = window.innerWidth / 2;
  let mouseY = window.innerHeight / 2;
  let glowX = mouseX;
  let glowY = mouseY;
  let isVisible = false;

  document.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;

    if (!isVisible) {
      isVisible = true;
      dot.style.opacity = '1';
      glow.style.opacity = '1';
    }

    // Dot snaps immediately
    dot.style.left = `${mouseX}px`;
    dot.style.top = `${mouseY}px`;
  });

  // Glow smoothly lags slightly behind using requestAnimationFrame
  function renderGlow() {
    glowX += (mouseX - glowX) * 0.18;
    glowY += (mouseY - glowY) * 0.18;

    glow.style.left = `${glowX}px`;
    glow.style.top = `${glowY}px`;

    requestAnimationFrame(renderGlow);
  }
  requestAnimationFrame(renderGlow);

  // Expand cursor over clickable elements
  const interactables = 'a, button, input, select, textarea, .btn, .card, [role="button"], .clickable';
  document.addEventListener('mouseover', (e) => {
    if (e.target.closest(interactables)) {
      document.body.classList.add('cursor-hover');
    }
  });

  document.addEventListener('mouseout', (e) => {
    if (e.target.closest(interactables)) {
      document.body.classList.remove('cursor-hover');
    }
  });

  document.addEventListener('mouseleave', () => {
    dot.style.opacity = '0';
    glow.style.opacity = '0';
    isVisible = false;
  });

  document.addEventListener('mouseenter', () => {
    dot.style.opacity = '1';
    glow.style.opacity = '1';
    isVisible = true;
  });
}

/* ==========================================================================
   HOMEPAGE OPENING ANIMATION
   ========================================================================== */
function initOpeningAnimation() {
  const animatedElement = document.querySelector('.brand-opening-animated');
  if (!animatedElement) return;

  // Runs once on homepage load
  animatedElement.classList.add('brand-opening-animated');
}

/* ==========================================================================
   MOBILE NAV TOGGLE
   ========================================================================== */
function initMobileNav() {
  const toggleBtn = document.querySelector('.nav-toggle');
  const navMenu = document.querySelector('.nav-menu');
  if (!toggleBtn || !navMenu) return;

  toggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    navMenu.classList.toggle('show');
  });

  document.addEventListener('click', (e) => {
    if (!navMenu.contains(e.target) && !toggleBtn.contains(e.target)) {
      navMenu.classList.remove('show');
    }
  });
}

/* ==========================================================================
   DEMO QUICK SWITCHER DROPDOWN
   ========================================================================== */
function initDemoSwitcher() {
  const demoBtn = document.getElementById('demoDropdownBtn');
  const demoMenu = document.getElementById('demoDropdownMenu');
  if (!demoBtn || !demoMenu) return;

  demoBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    demoMenu.classList.toggle('show');
  });

  document.addEventListener('click', () => {
    demoMenu.classList.remove('show');
  });
}

/* ==========================================================================
   HOW IT WORKS TIMELINE TOGGLE
   ========================================================================== */
function initTimelineToggle() {
  const studentBtn = document.getElementById('timeline-student-btn');
  const clientBtn = document.getElementById('timeline-client-btn');
  const studentList = document.getElementById('timeline-student-list');
  const clientList = document.getElementById('timeline-client-list');

  if (!studentBtn || !clientBtn || !studentList || !clientList) return;

  studentBtn.addEventListener('click', () => {
    studentBtn.classList.add('active');
    clientBtn.classList.remove('active');
    studentList.style.display = 'flex';
    clientList.style.display = 'none';
  });

  clientBtn.addEventListener('click', () => {
    clientBtn.classList.add('active');
    studentBtn.classList.remove('active');
    clientList.style.display = 'flex';
    studentList.style.display = 'none';
  });
}

/* ==========================================================================
   AUTO DISMISS FLASH ALERTS
   ========================================================================== */
function initFlashDismiss() {
  const alerts = document.querySelectorAll('.flash-alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-10px)';
      setTimeout(() => alert.remove(), 400);
    }, 4500);
  });
}
