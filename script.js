const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('.site-nav');

menuButton.addEventListener('click', () => {
  const isOpen = navigation.classList.toggle('open');
  menuButton.setAttribute('aria-expanded', String(isOpen));
  menuButton.querySelector('span').textContent = isOpen ? 'Close' : 'Menu';
  document.body.style.overflow = isOpen ? 'hidden' : '';
});

navigation.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    navigation.classList.remove('open');
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.querySelector('span').textContent = 'Menu';
    document.body.style.overflow = '';
  });
});

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });

document.querySelectorAll('.reveal').forEach((element) => observer.observe(element));

document.querySelectorAll('[data-language-switcher]').forEach((switcher) => {
  const buttons = switcher.querySelectorAll('button');
  const article = switcher.closest('.article-page');

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      article.dataset.language = button.dataset.language;
      buttons.forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
    });
  });
});
