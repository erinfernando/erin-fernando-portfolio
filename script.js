/* ── Mobile nav toggle ── */
(function () {
  const toggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');

  if (!toggle || !navLinks) return;

  toggle.addEventListener('click', function () {
    navLinks.classList.toggle('open');
    toggle.setAttribute('aria-expanded', navLinks.classList.contains('open'));
  });

  /* Close menu when any nav link is clicked */
  navLinks.addEventListener('click', function (e) {
    if (e.target.tagName === 'A') {
      navLinks.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    }
  });
})();

/* ── Scroll spy ── */
/* Highlights the nav link matching the section currently in view. */
(function () {
  var sections = document.querySelectorAll('section[id]');
  var navLinks = document.querySelectorAll('.nav-links a[href^="#"]');

  if (!sections.length || !navLinks.length) return;

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        navLinks.forEach(function (link) {
          link.classList.toggle(
            'active',
            link.getAttribute('href') === '#' + entry.target.id
          );
        });
      }
    });
  }, { rootMargin: '-20% 0px -60% 0px' });

  sections.forEach(function (section) { observer.observe(section); });
})();

/* ── Contact obfuscation ── */
/* Email is assembled at runtime so crawlers reading
   the static HTML never see a harvestable address. */
(function () {
  var u = 'fernando.erin.c';
  var d = 'gmail.com';
  var addr = u + '@' + d;

  document.querySelectorAll('[data-contact="email"]').forEach(function (el) {
    var a = document.createElement('a');
    a.href = 'mai' + 'lto:' + addr;
    a.textContent = addr;
    el.textContent = '';
    el.appendChild(a);
  });

  /* Phone number removed — Harvey flagged PII exposure risk on public site */
})();
