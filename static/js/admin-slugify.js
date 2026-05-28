(function () {
  function transliterate(text) {
    const map = {
      "а": "a", "б": "b", "в": "v", "г": "g", "ґ": "g",
      "д": "d", "е": "e", "ё": "yo", "є": "ye", "ж": "zh",
      "з": "z", "и": "i", "і": "i", "ї": "yi", "й": "y",
      "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
      "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
      "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh",
      "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e",
      "ю": "yu", "я": "ya"
    };

    return text
      .toLowerCase()
      .split("")
      .map(function (char) {
        return map[char] || char;
      })
      .join("")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-");
  }

  function initAdminSlugify() {
    const titleInput = document.querySelector("#id_title");
    const slugInput = document.querySelector("#id_slug");

    if (!titleInput || !slugInput) {
      return;
    }

    if (slugInput.dataset.adminSlugifyReady === "1") {
      return;
    }

    slugInput.dataset.adminSlugifyReady = "1";

    function updateSlug() {
      const newSlug = transliterate(titleInput.value);

      if (newSlug) {
        slugInput.value = newSlug;
      }
    }

    function scheduleUpdateSlug() {
      updateSlug();

      // Эти задержки нужны, чтобы перебить стандартный JS Wagtail,
      // который иногда после нас снова вставляет кириллицу.
      setTimeout(updateSlug, 50);
      setTimeout(updateSlug, 150);
      setTimeout(updateSlug, 300);
    }

    titleInput.addEventListener("input", scheduleUpdateSlug);
    titleInput.addEventListener("keyup", scheduleUpdateSlug);
    titleInput.addEventListener("change", scheduleUpdateSlug);
  }

  document.addEventListener("DOMContentLoaded", initAdminSlugify);
  window.addEventListener("load", initAdminSlugify);

  // На случай, если Wagtail подгрузил поля не сразу.
  setTimeout(initAdminSlugify, 300);
  setTimeout(initAdminSlugify, 1000);
})();