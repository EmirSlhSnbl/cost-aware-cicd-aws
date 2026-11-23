// Sepet tarayıcıda tutulur (localStorage). Sunucuda durum yok.
(function () {
  "use strict";
  var KEY = "cart-v1";
  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; }
  }
  function save(c) {
    try { localStorage.setItem(KEY, JSON.stringify(c)); } catch (e) { /* özel pencere */ }
  }
  function count(c) {
    return Object.keys(c).reduce(function (n, k) { return n + c[k]; }, 0);
  }
  function badge() {
    var el = document.getElementById("cart-count");
    if (el) el.textContent = count(load());
  }
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (t.classList.contains("add")) {
      var c = load(); c[t.dataset.id] = (c[t.dataset.id] || 0) + 1; save(c); badge();
    }
    if (t.id === "clear") { save({}); badge(); render(); }
  });
  function render() {
    var box = document.getElementById("cart-items");
    if (!box) return;
    fetch("/api/products").then(function (r) { return r.json(); }).then(function (list) {
      var c = load(), total = 0;
      box.textContent = "";
      list.forEach(function (p) {
        var q = c[p.id];
        if (!q) return;
        total += q * p.price;
        var row = document.createElement("p");
        row.textContent = p.name + " × " + q + " = " + (q * p.price).toFixed(2) + " ₺";
        box.appendChild(row);
      });
      if (!box.children.length) box.textContent = "Sepetiniz boş.";
      document.getElementById("cart-total").textContent = total.toFixed(2);
    });
  }
  badge(); render();
})();