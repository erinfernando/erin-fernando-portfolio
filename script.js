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

/* ── Contact obfuscation ── */
/* Email and phone are assembled at runtime so crawlers reading
   the static HTML never see a harvestable address or number. */
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

  var p1 = '(858) 243';
  var p2 = '-6917';
  var phone = p1 + p2;

  document.querySelectorAll('[data-contact="phone"]').forEach(function (el) {
    el.textContent = phone;
  });
})();
