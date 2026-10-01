(function () {
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches || document.documentElement.dataset.motion === "reduced";

  // боковое меню: сворачивание, тема, поиск (состояние запоминается)
  var sidebar = document.getElementById("sidebar");
  var toggle = document.getElementById("sideToggle");
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  if (sidebar && toggle) {
    var narrow = window.matchMedia("(max-width: 800px)").matches;
    var collapsed = narrow ? true : store.get("sidebar") === "collapsed";
    var apply = function () {
      sidebar.classList.toggle("collapsed", collapsed);
      document.body.classList.toggle("side-collapsed", collapsed);
      toggle.setAttribute("aria-expanded", String(!collapsed));
    };
    apply();
    toggle.addEventListener("click", function () {
      collapsed = !collapsed; apply();
      store.set("sidebar", collapsed ? "collapsed" : "open");
    });
    var searchIcon = document.getElementById("searchIcon");
    var searchInput = document.getElementById("sideSearch");
    if (searchIcon && searchInput) {
      searchIcon.addEventListener("click", function () {
        if (collapsed) { collapsed = false; apply(); setTimeout(function () { searchInput.focus(); }, 300); }
        else if (searchInput.value.trim()) { searchInput.form.submit(); }
        else { searchInput.focus(); }
      });
    }
  }
  var themeBtn = document.getElementById("themeToggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var dark = document.documentElement.dataset.theme !== "dark";
      document.documentElement.dataset.theme = dark ? "dark" : "light";
      store.set("theme", dark ? "dark" : "light");
    });
  }

  // страница настроек: тема, меню, анимации (хранится в браузере)
  document.querySelectorAll("[data-setting]").forEach(function (el) {
    var key = el.dataset.setting, root = document.documentElement;
    if (key === "theme") {
      el.checked = (root.dataset.theme || "light") === el.value;
      el.addEventListener("change", function () { root.dataset.theme = el.value; store.set("theme", el.value); });
    } else if (key === "fontsize") {
      el.checked = (root.dataset.fontsize || "normal") === el.value;
      el.addEventListener("change", function () { root.dataset.fontsize = el.value; store.set("fontsize", el.value); });
    } else if (key === "sidebar") {
      el.checked = store.get("sidebar") === "collapsed";
      el.addEventListener("change", function () { store.set("sidebar", el.checked ? "collapsed" : "open"); });
    } else if (key === "motion") {
      el.checked = store.get("motion") === "reduced";
      el.addEventListener("change", function () {
        if (el.checked) { root.dataset.motion = "reduced"; store.set("motion", "reduced"); }
        else { delete root.dataset.motion; store.set("motion", "normal"); }
      });
    }
  });

  // появление при прокрутке
  var items = document.querySelectorAll(".reveal");
  if (reduce || !("IntersectionObserver" in window)) {
    items.forEach(function (el) { el.classList.add("visible"); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("visible"); io.unobserve(e.target); }
      });
    }, { threshold: 0.15 });
    items.forEach(function (el, i) { el.style.transitionDelay = (i % 3) * 80 + "ms"; io.observe(el); });
  }

  // счётчики
  document.querySelectorAll("[data-count]").forEach(function (el) {
    var target = parseInt(el.dataset.count, 10) || 0;
    if (reduce || target === 0) { el.textContent = target; return; }
    var n = 0, step = Math.max(1, Math.round(target / 50));
    var t = setInterval(function () {
      n = Math.min(target, n + step);
      el.textContent = n;
      if (n === target) clearInterval(t);
    }, 25);
  });
})();
