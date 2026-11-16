// Runs before first paint so the saved theme never flashes; kept external for the site's script policy.
(function () {
  var saved = null;
  try { saved = localStorage.getItem('footballknow-theme'); } catch (error) { saved = null; }
  var dark = saved ? saved === 'dark' : window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
})();
