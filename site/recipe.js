(function () {
  // Tick-off ingredients and steps while cooking. State is in-memory only.
  var article = document.querySelector(".recipe");
  if (!article) return;

  // Checkboxes only on the ingredient list: the first <ul> after the
  // "Ingredients" heading, or the first <ul> if there is no such heading.
  var ingredients = null;
  article.querySelectorAll("h2").forEach(function (h) {
    if (!ingredients && /ingredients/i.test(h.textContent)) {
      var el = h.nextElementSibling;
      while (el && el.tagName !== "UL" && el.tagName !== "H2") el = el.nextElementSibling;
      if (el && el.tagName === "UL") ingredients = el;
    }
  });
  if (!ingredients) ingredients = article.querySelector("ul");
  var items = ingredients ? ingredients.querySelectorAll("li") : [];
  items.forEach(function (li) {
    var box = document.createElement("input");
    box.type = "checkbox";
    box.setAttribute("aria-label", "done");
    li.insertBefore(box, li.firstChild);
    box.addEventListener("change", function () {
      li.classList.toggle("done", box.checked);
    });
  });

  article.querySelectorAll("ol li").forEach(function (li) {
    li.addEventListener("click", function () {
      li.classList.toggle("done");
    });
  });

  var reset = document.getElementById("reset");
  if (reset) {
    reset.addEventListener("click", function () {
      article.querySelectorAll("li.done").forEach(function (li) { li.classList.remove("done"); });
      article.querySelectorAll("input[type=checkbox]").forEach(function (b) { b.checked = false; });
    });
  }

  // Screen wake lock, where the browser supports it (needs https).
  var wake = document.getElementById("wake");
  var lock = null;
  if (wake) {
    if (!("wakeLock" in navigator)) {
      wake.hidden = true;
    } else {
      wake.addEventListener("click", function () {
        if (lock) {
          lock.release();
          lock = null;
          wake.classList.remove("on");
          return;
        }
        navigator.wakeLock.request("screen").then(function (l) {
          lock = l;
          wake.classList.add("on");
          l.addEventListener("release", function () {
            lock = null;
            wake.classList.remove("on");
          });
        }).catch(function () {});
      });
    }
  }
})();
