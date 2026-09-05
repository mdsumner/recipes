(function () {
  var q = document.getElementById("q");
  var cards = Array.prototype.slice.call(document.querySelectorAll("#cards .card"));
  var tagLinks = Array.prototype.slice.call(document.querySelectorAll("#tags .tag"));
  var none = document.getElementById("none");
  var tag = "";
  var index = null;

  function param(name) {
    var m = new RegExp("[?&]" + name + "=([^&]*)").exec(location.search);
    return m ? decodeURIComponent(m[1].replace(/\+/g, " ")) : "";
  }

  function apply() {
    var text = (q.value || "").toLowerCase().trim();
    var shown = 0;
    cards.forEach(function (c) {
      var tags = " " + c.getAttribute("data-tags") + " ";
      var ok = !tag || tags.indexOf(" " + tag + " ") >= 0;
      if (ok && text) {
        var hay = c.textContent.toLowerCase();
        if (index && index[c.getAttribute("data-slug")]) {
          hay += " " + index[c.getAttribute("data-slug")];
        }
        ok = text.split(/\s+/).every(function (w) { return hay.indexOf(w) >= 0; });
      }
      c.hidden = !ok;
      if (ok) shown++;
    });
    none.hidden = shown > 0;
    tagLinks.forEach(function (a) {
      a.classList.toggle("on", a.getAttribute("data-tag") === tag);
    });
  }

  tagLinks.forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      tag = a.getAttribute("data-tag");
      apply();
    });
  });
  q.addEventListener("input", apply);

  tag = param("tag");
  q.value = param("q");
  apply();

  // Full-text index (ingredients and steps) loads lazily; search works on
  // titles and tags before it arrives.
  try {
    fetch("recipes.json").then(function (r) { return r.json(); }).then(function (rows) {
      index = {};
      rows.forEach(function (r) { index[r.slug] = r.search || ""; });
      apply();
    }).catch(function () {});
  } catch (e) {}
})();
