/* ==========================================================================
   ONE PLACE TO EDIT YOUR BUSINESS DETAILS
   Change the values below and every page updates.

   TRUTH RULE: only put CONFIRMED facts here. Anything not confirmed by the
   business owner must stay out of the site entirely — an empty placeholder is
   safer than an invented one.
   ========================================================================== */

const SITE = {
  name:    "The Aly Touch",
  tagline: "Cleaning for floors, work surfaces, bathrooms, shower rooms, beds, linen and ovens",
  phone:   "07781 446239"
};

/* --------------------------------------------------------------------------
   Everything below is plumbing — you shouldn't need to touch it.
   -------------------------------------------------------------------------- */

// Flag that JS is running. Entrance animations are gated on this, so content
// is never hidden when the script fails to load.
document.documentElement.classList.add("js-ready");

document.addEventListener("DOMContentLoaded", () => {
  document.body.classList.add("js-ready");

  // Fill in every [data-site="key"] placeholder from SITE above. Keys that are
  // not defined are removed rather than left as empty gaps.
  document.querySelectorAll("[data-site]").forEach(el => {
    const value = SITE[el.dataset.site];
    if (value === undefined) { el.remove(); return; }
    el.textContent = value;
  });

  // Telephone links. Digits only, no spaces, so the dialler gets a clean number.
  document.querySelectorAll('[data-href="phone"]').forEach(el => {
    el.setAttribute("href", "tel:" + SITE.phone.replace(/[^0-9+]/g, ""));
  });

  // Page title prefix.
  document.title = document.title.replace("%SITE%", SITE.name);

  // Mobile navigation. Visibility is driven by CSS (the .is-open class on the
  // header), so resizing the window can never leave the menu stuck hidden.
  const toggle = document.querySelector(".nav-toggle");
  const header = document.querySelector(".site-header");
  const nav = document.getElementById("primary-nav");
  if (toggle && header && nav) {
    toggle.addEventListener("click", () => {
      const open = header.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    nav.addEventListener("click", e => {
      if (e.target.closest("a")) {
        header.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape" && header.classList.contains("is-open")) {
        header.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
    });
  }

  // Mark the current page in the nav.
  const here = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav a[href]").forEach(a => {
    if (a.getAttribute("href") === here) a.setAttribute("aria-current", "page");
  });

  // Footer year.
  const year = document.querySelector("[data-year]");
  if (year) year.textContent = new Date().getFullYear();

  /* ---------------------------------------------------------------- sliders
     Before/after comparison. The markup lives in the HTML, not in here — if
     this script never runs, the visitor still sees a real "before" image and
     a real "after" image, never a misleading fallback.

     Pointer events cover mouse, touch and pen in one path; arrow keys make it
     usable without a mouse.
     ------------------------------------------------------------------------ */
  document.querySelectorAll("[data-ba]").forEach(ba => {
    const wrap = ba.querySelector(".ba__after-wrap");
    if (!wrap) return;

    const setPos = pct => {
      const p = Math.min(100, Math.max(0, pct));
      ba.style.setProperty("--ba-pos", p + "%");
      // Counter-scale the clipped image so it does not squash as the wrap narrows.
      wrap.style.setProperty("--ba-width", (p === 0 ? 100 : (100 / p) * 100) + "%");
      ba.setAttribute("aria-valuenow", Math.round(p));
    };
    const fromEvent = e => {
      const r = ba.getBoundingClientRect();
      if (!r.width) return;
      setPos(((e.clientX - r.left) / r.width) * 100);
    };

    let dragging = false;
    ba.addEventListener("pointerdown", e => {
      dragging = true;
      try { ba.setPointerCapture(e.pointerId); } catch (err) { /* not fatal */ }
      fromEvent(e);
      e.preventDefault();
    });
    ba.addEventListener("pointermove", e => { if (dragging) fromEvent(e); });
    ba.addEventListener("pointerup",     () => { dragging = false; });
    ba.addEventListener("pointercancel", () => { dragging = false; });
    // Touch scrolling must not fight the drag once it has started.
    ba.addEventListener("touchmove", e => { if (dragging) e.preventDefault(); },
                        { passive: false });

    ba.addEventListener("keydown", e => {
      const now = parseFloat(ba.getAttribute("aria-valuenow")) || 50;
      if (e.key === "ArrowLeft")  { setPos(now - 5); e.preventDefault(); }
      if (e.key === "ArrowRight") { setPos(now + 5); e.preventDefault(); }
      if (e.key === "Home")       { setPos(0);   e.preventDefault(); }
      if (e.key === "End")        { setPos(100); e.preventDefault(); }
    });

    setPos(50);
  });

  // Back to top. Built in JS so every page gets it without extra markup.
  const toTop = document.createElement("button");
  toTop.type = "button";
  toTop.className = "to-top";
  toTop.setAttribute("aria-label", "Back to top");
  toTop.innerHTML = "&uarr;";
  toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  document.body.appendChild(toTop);
  const toggleTopBtn = () => toTop.classList.toggle("is-visible", window.scrollY > 600);
  window.addEventListener("scroll", toggleTopBtn, { passive: true });
  toggleTopBtn();

  /* Enquiry form.
     This does NOT send anything anywhere yet — it confirms on screen only.
     To make it really send, point the <form> at a form service (Formspree,
     Netlify Forms, Web3Forms) or your own endpoint, and delete this block. */
  const form = document.querySelector("[data-demo-form]");
  if (form) {
    const status = form.querySelector(".form-status");
    form.addEventListener("submit", e => {
      e.preventDefault();
      if (!form.reportValidity()) return;
      const nameField = form.querySelector("#name");
      const name = (nameField && nameField.value.trim()) || "";
      status.hidden = false;
      status.textContent = name
        ? `Thanks ${name.split(" ")[0]} — this form is not connected yet, so nothing was sent. Please call ${SITE.phone} in the meantime.`
        : `This form is not connected yet, so nothing was sent. Please call ${SITE.phone} in the meantime.`;
      status.scrollIntoView({ block: "nearest", behavior: "smooth" });
      form.reset();
    });
  }
});
