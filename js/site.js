/* ==========================================================================
   ONE PLACE TO EDIT YOUR BUSINESS DETAILS
   Change the values below and every page updates.

   TRUTH RULE: only put CONFIRMED facts here. Anything not confirmed by the
   business owner must stay out of the site entirely — an empty placeholder is
   safer than an invented one.
   ========================================================================== */

const SITE = {
  name:    "The Aly Touch",
  tagline: "Home cleaning, extra jobs like ovens, fridges and windows, and one-off jobs from deep cleans to end of tenancy",
  phone:   "07781 446239",

  // Where the service operates. Used in headings, the footer and the schema
  // block, so changing it here changes it everywhere.
  area:    "Guernsey",

  // Headline rate. DELIBERATELY BLANK — the site does not publish a price.
  // Put a figure here (e.g. "£35") and every price block switches back on;
  // the copy around them is already written for it.
  rate:    "",
  rateNote: "The hours are estimated and agreed with you before anything is booked.",

  // A real photo of Aly for the About page. Drop the file into img/ and put the
  // path here (e.g. "img/aly.jpg"). Until it is set, the About page keeps the
  // logo panel — it never shows a broken or empty frame.
  portrait:     "",
  portraitAlt:  "Aly, who runs The Aly Touch",
  portraitName: "Aly",
  portraitRole: "Owner, The Aly Touch",
  // Add the approved secure form endpoint here after the business email and
  // delivery service have been configured. Leave blank to keep delivery off.
  quoteDelivery: { endpoint: "https://formsubmit.co/ajax/contact@thealytouch.co.uk" }
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

  // Any element marked [data-needs="key"] disappears when that SITE value is
  // blank. An unfinished-looking empty panel is worse than no panel.
  document.querySelectorAll("[data-needs]").forEach(el => {
    if (!SITE[el.dataset.needs]) el.remove();
  });

  // About page portrait. Swapped in only when SITE.portrait names a real file.
  const aboutMedia = document.querySelector("[data-about-media]");
  if (aboutMedia && SITE.portrait) {
    aboutMedia.innerHTML =
      '<figure class="portrait" style="margin:0">' +
        '<img src="" alt="" width="1000" height="1250" loading="lazy" decoding="async">' +
        '<figcaption class="portrait__caption"><strong></strong><span></span></figcaption>' +
      '</figure>';
    const img = aboutMedia.querySelector("img");
    img.src = SITE.portrait;
    img.alt = SITE.portraitAlt || "";
    aboutMedia.querySelector("strong").textContent = SITE.portraitName || "";
    aboutMedia.querySelector("span").textContent = SITE.portraitRole || "";
  }

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

  // The Aly Touch quote flow deliberately stays on this page. Delivery remains
  // inactive until SITE.quoteDelivery.endpoint is configured with an approved
  // secure receiver; it never redirects to the separate Mrs Jones questionnaire.
  const quoteForm = document.querySelector("[data-quote-form]");
  if (quoteForm) {
    const steps = [...quoteForm.querySelectorAll("[data-quote-step]")];
    const stepLinks = [...quoteForm.querySelectorAll(".quote-flow__steps li")];
    const progress = quoteForm.querySelector("[data-quote-progress]");
    const back = quoteForm.querySelector("[data-quote-back]");
    const next = quoteForm.querySelector("[data-quote-next]");
    const submit = quoteForm.querySelector("[data-quote-submit]");
    const status = quoteForm.querySelector("[data-quote-status]");
    const serviceError = quoteForm.querySelector("[data-service-error]");
    const summary = quoteForm.querySelector("[data-quote-summary]");
    const labels = ["Your details", "Your clean", "Your routine", "Check your request"];
    let current = 0;


    /* ---------------------------------------------------------------- photos
       Up to six pictures of the rooms. Held in memory as File objects and shown
       as thumbnails; the native file input is never re-read, because picking a
       second time would otherwise replace the first selection rather than add
       to it. Object URLs are revoked on removal so the tab does not leak. */
    const MAX_PHOTOS = 6;
    const MAX_BYTES = 10 * 1024 * 1024;
    const photoInput = quoteForm.querySelector("[data-photo-input]");
    const photoList = quoteForm.querySelector("[data-photo-list]");
    const photoCount = quoteForm.querySelector("[data-photo-count]");
    let photos = [];

    const describePhotos = extra => {
      if (!photoCount) return;
      const n = photos.length;
      photoCount.textContent =
        (n === 0 ? "No photos added yet." : `${n} photo${n === 1 ? "" : "s"} added${n >= MAX_PHOTOS ? " — that is the maximum" : ""}.`) +
        (extra ? " " + extra : "");
    };

    const renderPhotos = extra => {
      if (!photoList) return;
      photoList.querySelectorAll("img").forEach(img => URL.revokeObjectURL(img.src));
      photoList.innerHTML = "";
      photos.forEach((file, index) => {
        const item = document.createElement("li");
        const img = document.createElement("img");
        img.src = URL.createObjectURL(file);
        img.alt = "";
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "photo-remove";
        remove.textContent = "Remove";
        remove.setAttribute("aria-label", `Remove photo ${index + 1}, ${file.name}`);
        remove.addEventListener("click", () => {
          photos.splice(index, 1);
          renderPhotos();
        });
        item.append(img, remove);
        photoList.append(item);
      });
      describePhotos(extra);
    };

    if (photoInput) {
      photoInput.addEventListener("change", () => {
        const picked = [...photoInput.files];
        const images = picked.filter(f => f.type.startsWith("image/"));
        const small = images.filter(f => f.size <= MAX_BYTES);
        const room = Math.max(0, MAX_PHOTOS - photos.length);
        photos = photos.concat(small.slice(0, room));

        const notes = [];
        if (picked.length !== images.length) notes.push("Some files were not pictures and were skipped.");
        if (images.length !== small.length) notes.push("Some pictures were over 10MB and were skipped.");
        if (small.length > room) notes.push(`Only the first ${room} could be added.`);
        // Clearing the input means choosing the same file again still fires change.
        photoInput.value = "";
        renderPhotos(notes.join(" "));
      });
      renderPhotos();
    }

    const selectedServices = () => [...quoteForm.querySelectorAll('input[name="service"]:checked')].map(input => input.value);
    const showStep = index => {
      current = index;
      steps.forEach((step, i) => { step.hidden = i !== current; });
      stepLinks.forEach((item, i) => { if (i === current) item.setAttribute("aria-current", "step"); else item.removeAttribute("aria-current"); });
      progress.textContent = `Step ${current + 1} of 4: ${labels[current]}`;
      back.hidden = current === 0;
      next.hidden = current === steps.length - 1;
      submit.hidden = current !== steps.length - 1;
      status.hidden = true;
      if (current === steps.length - 1) updateSummary();
      const focusTarget = steps[current].querySelector("input, select, textarea");
      if (focusTarget) focusTarget.focus({ preventScroll: true });
    };
    const validStep = () => {
      const inputs = [...steps[current].querySelectorAll("input, select, textarea")];
      if (current === 1 && selectedServices().length === 0) {
        serviceError.hidden = false;
        serviceError.textContent = "Please choose at least one task, or select Not sure yet.";
        return false;
      }
      serviceError.hidden = true;
      return inputs.every(input => input.checkValidity()) ? true : (steps[current].querySelector("input:invalid, select:invalid, textarea:invalid") || quoteForm).reportValidity();
    };
    const updateSummary = () => {
      const value = name => (quoteForm.elements[name] && quoteForm.elements[name].value.trim()) || "Not provided";
      const rows = [["Name", value("name")], ["Phone", value("phone")], ["Email", value("email")], ["Tasks", selectedServices().join(", ") || "Not provided"], ["Frequency", value("frequency")], ["Postcode or parish", value("postcode")], ["Photos", photos.length ? `${photos.length} attached` : "None"], ["Notes", value("message")]];
      summary.innerHTML = rows.map(([term, detail]) => `<div><dt>${term}</dt><dd>${detail}</dd></div>`).join("");
    };
    next.addEventListener("click", () => { if (validStep()) showStep(current + 1); });
    back.addEventListener("click", () => showStep(current - 1));
    // Human-readable labels for the notification email. FormSubmit uses the
    // field name verbatim as the label, so payload keys are renamed here
    // rather than in the form itself (the form's own field names are still
    // used by validation and the on-page summary above).
    const FIELD_LABELS = {
      name: "Name",
      phone: "Phone",
      email: "Email",
      services: "Tasks selected",
      frequency: "How often",
      postcode: "Postcode or parish",
      message: "Tell us about your place",
      consent: "Agreed to be contacted"
    };
    const labelKey = key => FIELD_LABELS[key] || key;

    quoteForm.addEventListener("submit", async e => {
      e.preventDefault();
      if (!quoteForm.reportValidity()) return;
      const endpoint = SITE.quoteDelivery && SITE.quoteDelivery.endpoint;
      status.hidden = false;
      if (!endpoint) {
        status.textContent = `Nothing has been sent — this form cannot deliver your details yet. Please call ${SITE.phone} and we will take it from there. Your answers are still above if you want to read them out.`;
        status.scrollIntoView({ block: "nearest", behavior: "smooth" });
        return;
      }
      // The AJAX endpoint (SITE.quoteDelivery.endpoint) does not deliver file
      // attachments — FormSubmit only sends photos through its classic,
      // non-AJAX endpoint. That endpoint returns an HTML page rather than
      // JSON, so success is instead confirmed by checking its page text.
      const classicEndpoint = endpoint.replace("/ajax/", "/");
      const usingClassicEndpoint = photos.length > 0;
      let request;
      if (photos.length) {
        const raw = Object.fromEntries(new FormData(quoteForm).entries());
        delete raw.photos;
        delete raw.service;
        const form = new FormData();
        for (const [key, value] of Object.entries(raw)) {
          form.append(labelKey(key), value);
        }
        form.append(labelKey("services"), selectedServices().join(", ") || "Not provided");
        photos.forEach(file => form.append("Photos", file, file.name));
        form.append("_subject", "New enquiry - The Aly Touch quote form");
        form.append("_captcha", "false");
        // No Content-Type header: the browser sets the multipart boundary.
        request = { method: "POST", body: form };
      } else {
        const raw = Object.fromEntries(new FormData(quoteForm).entries());
        delete raw.photos;
        delete raw.service;
        const payload = {};
        for (const [key, value] of Object.entries(raw)) {
          payload[labelKey(key)] = value;
        }
        payload[labelKey("services")] = selectedServices();
        payload._subject = "New enquiry - The Aly Touch quote form";
        payload._captcha = "false";
        request = { method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/json" }, body: JSON.stringify(payload) };
      }
      try {
        const response = await fetch(usingClassicEndpoint ? classicEndpoint : endpoint, request);
        let delivered;
        if (usingClassicEndpoint) {
          const text = await response.text();
          delivered = response.ok && (text.includes("submitted successfully") || text.includes("Thanks!"));
        } else {
          let result = null;
          try { result = await response.json(); } catch (parseErr) { /* endpoint returned non-JSON; treat as failure below */ }
          delivered = response.ok && result && (result.success === true || result.success === "true");
        }
        if (!delivered) throw new Error("Delivery unavailable");
        quoteForm.hidden = true;
        const success = document.querySelector("[data-quote-success]");
        if (success) { success.hidden = false; success.scrollIntoView({ block: "nearest", behavior: "smooth" }); }
      } catch (error) {
        status.textContent = `Your request did not go through. Please call ${SITE.phone} and we will sort it out.`;
        status.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    });
  }
});
