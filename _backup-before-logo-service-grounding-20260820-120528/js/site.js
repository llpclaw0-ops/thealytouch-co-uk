/* ==========================================================================
   ONE PLACE TO EDIT YOUR BUSINESS DETAILS
   Change the values below and every page updates.
   ========================================================================== */

const SITE = {
  name:     "Mrs. Jones Touch",
  tagline:  "Home & office cleaning you can rely on",
  phone:    "01481 000 000",
  email:    "hello@mrsjonestouch.gg",
  area:     "Guernsey",
  address:  "St Peter Port, Guernsey",
  hours:    "Mon–Sat, 8am–6pm",
  founded:  "2026",

  // Leave any of these empty ("") and the link simply won't appear.
  // No empty social icons, no links to nowhere.
  social: {
    instagram: "",
    facebook:  "",
    youtube:   "",
    linkedin:  ""
  },

  // Paste the Google Maps link for the business address here to make the
  // footer address clickable. Leave empty for plain text.
  mapUrl: ""
};

/* --------------------------------------------------------------------------
   Everything below is plumbing — you shouldn't need to touch it.
   -------------------------------------------------------------------------- */

// Flag that JS is running. The hero entrance animation is gated on this, so
// the hero is never hidden when the script fails to load.
document.documentElement.classList.add("js-ready");
document.body && document.body.classList.add("js-ready");

document.addEventListener("DOMContentLoaded", () => {
  document.body.classList.add("js-ready");
  // Fill in every [data-site="key"] placeholder from SITE above.
  document.querySelectorAll("[data-site]").forEach(el => {
    const value = SITE[el.dataset.site];
    if (value === undefined) return;
    el.textContent = value;
  });

  // Phone and email links.
  document.querySelectorAll('[data-href="phone"]').forEach(el => {
    el.setAttribute("href", "tel:" + SITE.phone.replace(/\s+/g, ""));
  });
  document.querySelectorAll('[data-href="email"]').forEach(el => {
    el.setAttribute("href", "mailto:" + SITE.email);
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
    // Close the menu after tapping a link.
    nav.addEventListener("click", e => {
      if (e.target.closest("a")) {
        header.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Mark the current page in the nav.
  const here = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav a[href]").forEach(a => {
    if (a.getAttribute("href") === here) a.setAttribute("aria-current", "page");
  });

  // Footer social links — only the ones that have been filled in.
  const socialHost = document.querySelector("[data-social]");
  if (socialHost) {
    const ICONS = { instagram: "Instagram", facebook: "Facebook", youtube: "YouTube", linkedin: "LinkedIn" };
    const links = Object.entries(SITE.social || {}).filter(([, url]) => url && url.trim());
    if (!links.length) {
      socialHost.remove();
    } else {
      socialHost.innerHTML = links.map(([key, url]) =>
        `<a class="social-link" href="${url}" target="_blank" rel="noopener noreferrer">${ICONS[key] || key}</a>`
      ).join("");
    }
  }

  // Make the address a map link when one is configured.
  document.querySelectorAll('[data-href="map"]').forEach(el => {
    if (SITE.mapUrl && SITE.mapUrl.trim()) {
      el.setAttribute("href", SITE.mapUrl);
      el.setAttribute("target", "_blank");
      el.setAttribute("rel", "noopener noreferrer");
    } else if (el.tagName === "A") {
      // no map configured — swap the link for plain text so nothing is dead
      const span = document.createElement("span");
      span.textContent = el.textContent;
      el.replaceWith(span);
    }
  });

  // Footer year.
  const year = document.querySelector("[data-year]");
  if (year) year.textContent = new Date().getFullYear();

  // Reviews carousel. Uses native scrolling, so it still works if JS is slow
  // to load and stays usable with a keyboard or a trackpad swipe.
  document.querySelectorAll("[data-carousel]").forEach(root => {
    const track = root.querySelector(".carousel__track");
    const prev  = root.querySelector("[data-carousel-prev]");
    const next  = root.querySelector("[data-carousel-next]");
    const dots  = root.querySelector("[data-carousel-dots]");
    const slides = [...track.children];
    if (!slides.length) return;

    // Page count comes from the track's own scroll width. Measuring individual
    // slides is unreliable before images settle and can report zero.
    const pages = () => Math.max(1, Math.ceil(track.scrollWidth / track.clientWidth - 0.05));
    const current = () => Math.min(pages() - 1, Math.round(track.scrollLeft / (track.clientWidth || 1)));

    const scrollToPage = i => {
      const target = Math.min(Math.max(i, 0), pages() - 1);
      track.scrollTo({ left: target * track.clientWidth, behavior: "smooth" });
      // Update the controls from the target directly. Scroll events are not
      // guaranteed (background tabs suppress them), so state must not depend
      // on them alone.
      sync(target);
    };

    function buildDots() {
      dots.innerHTML = "";
      for (let i = 0; i < pages(); i++) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "carousel__dot";
        b.setAttribute("aria-label", `Go to review page ${i + 1}`);
        b.addEventListener("click", () => scrollToPage(i));
        dots.appendChild(b);
      }
    }

    function sync(index) {
      const i = index === undefined ? current() : index;
      [...dots.children].forEach((d, n) => d.setAttribute("aria-current", String(n === i)));
      prev.disabled = i <= 0;
      next.disabled = i >= pages() - 1;
    }

    prev.addEventListener("click", () => scrollToPage(current() - 1));
    next.addEventListener("click", () => scrollToPage(current() + 1));
    // Sync directly rather than via requestAnimationFrame, which is throttled
    // in background tabs and leaves the dots out of step with the scroll.
    track.addEventListener("scroll", () => sync(), { passive: true });
    window.addEventListener("resize", () => { buildDots(); sync(); });

    buildDots();
    sync();
    window.addEventListener("load", () => { buildDots(); sync(); });
  });

  // Before/after sliders. Pointer events cover mouse, touch and pen in one
  // path; arrow keys make it usable without a mouse.
  document.querySelectorAll("[data-ba]").forEach(ba => {
    const wrap = ba.querySelector(".ba__after-wrap");
    const setPos = pct => {
      const p = Math.min(100, Math.max(0, pct));
      ba.style.setProperty("--ba-pos", p + "%");
      // Counter-scale the clipped image so it does not squash as the wrap narrows.
      wrap.style.setProperty("--ba-width", (p === 0 ? 100 : (100 / p) * 100) + "%");
      ba.setAttribute("aria-valuenow", Math.round(p));
    };
    const fromEvent = e => {
      const r = ba.getBoundingClientRect();
      setPos(((e.clientX - r.left) / r.width) * 100);
    };

    let dragging = false;
    ba.addEventListener("pointerdown", e => {
      dragging = true;
      ba.setPointerCapture(e.pointerId);
      fromEvent(e);
    });
    ba.addEventListener("pointermove", e => { if (dragging) fromEvent(e); });
    ba.addEventListener("pointerup",     () => { dragging = false; });
    ba.addEventListener("pointercancel", () => { dragging = false; });

    ba.addEventListener("keydown", e => {
      const now = parseFloat(ba.getAttribute("aria-valuenow")) || 50;
      if (e.key === "ArrowLeft")  { setPos(now - 4); e.preventDefault(); }
      if (e.key === "ArrowRight") { setPos(now + 4); e.preventDefault(); }
      if (e.key === "Home")       { setPos(0);  e.preventDefault(); }
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

  // Counting stats. Runs once when the block scrolls into view, and respects
  // a reduced-motion preference by jumping straight to the final number.
  const counters = document.querySelectorAll("[data-count]");
  if (counters.length) {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const render = (el, value) => {
      const dp = parseInt(el.dataset.decimals || "0", 10);
      el.textContent = value.toFixed(dp) + (el.dataset.suffix || "") + (el.dataset.plus || "");
    };
    const run = el => {
      const target = parseFloat(el.dataset.count);
      if (reduce) { render(el, target); return; }
      const started = performance.now();
      const step = now => {
        const t = Math.min(1, (now - started) / 1400);
        const eased = 1 - Math.pow(1 - t, 3);
        render(el, target * eased);
        if (t < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver(entries => {
        entries.forEach(e => {
          if (e.isIntersecting) { run(e.target); io.unobserve(e.target); }
        });
      }, { threshold: 0.4 });
      counters.forEach(el => io.observe(el));
    } else {
      counters.forEach(run);
    }
  }

  // Wrap plain button labels so they can do the hover slide. Done in JS so the
  // markup stays readable and the buttons still work with JS switched off.
  document.querySelectorAll(".btn").forEach(btn => {
    if (btn.querySelector(".btn__label")) return;
    const nodes = [...btn.childNodes];
    const textNode = nodes.find(n => n.nodeType === 3 && n.textContent.trim());
    if (!textNode) return;
    const text = textNode.textContent.trim();
    const label = document.createElement("span");
    label.className = "btn__label";
    const inner = document.createElement("span");
    inner.textContent = text;
    inner.setAttribute("data-label", text);
    label.appendChild(inner);
    btn.replaceChild(label, textNode);
  });

  // Scroll reveals. Classes are added by JS, never in the HTML, so if this
  // script never runs the page is simply visible rather than blank.
  (() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || !("IntersectionObserver" in window)) return;

    const groups = document.querySelectorAll(
      ".section-head, .grid, .split > *, .steps, .cta-band, .faq details, .job-meta, .stat-row"
    );
    const targets = [];
    groups.forEach(el => {
      // Skip anything inside the hero — that should be visible immediately.
      if (el.closest(".hero")) return;
      const isGroup = el.classList.contains("grid") || el.classList.contains("steps") || el.classList.contains("stat-row");
      el.classList.add(isGroup ? "reveal-group" : "reveal");
      targets.push(el);
    });

    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        e.target.classList.add("is-in");
        io.unobserve(e.target);
      });
      // threshold 0 = fire as soon as any part enters. A percentage threshold
      // is unreliable for blocks taller than the viewport.
    }, { threshold: 0, rootMargin: "0px 0px -8% 0px" });

    targets.forEach(el => {
      // Anything already on screen at load reveals straight away.
      const top = el.getBoundingClientRect().top;
      if (top < window.innerHeight * 0.9) { el.classList.add("is-in"); return; }
      io.observe(el);
    });

    // Backstops. Content must never be left invisible, so reveal everything
    // after a short delay regardless, and again once the page has fully loaded.
    const revealAll = () => targets.forEach(el => el.classList.add("is-in"));
    setTimeout(revealAll, 1600);
    window.addEventListener("load", () => setTimeout(revealAll, 400));
    window.addEventListener("pagehide", revealAll);
  })();

  /* Booking form.
     Right now this does NOT send anything anywhere — it just confirms on screen.
     To make it really send, point the <form> at a form service (Formspree,
     Netlify Forms, Web3Forms) or your own endpoint, and delete this block. */
  const form = document.querySelector("[data-demo-form]");
  if (form) {
    const status = form.querySelector(".form-status");
    form.addEventListener("submit", e => {
      e.preventDefault();
      if (!form.reportValidity()) return;
      const name = (form.querySelector("#name") || {}).value || "there";
      status.hidden = false;
      status.textContent =
        `Thanks ${name.split(" ")[0]} — this is the demo form, so nothing was sent yet. ` +
        `Connect it to a form service to receive real enquiries.`;
      status.scrollIntoView({ block: "nearest", behavior: "smooth" });
      form.reset();
    });
  }
});
