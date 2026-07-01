/* ==========================================================================
   Sentinela RJ — Dashboard Dark Carousel Template
   RENDER — lê CAROUSEL_CONFIG (config.js) e monta os slides no DOM.

   Não é necessário editar este arquivo para reutilizar o template.
   Toda a personalização acontece em config.js.
   ========================================================================== */

function buildSlide(cfg, slideCfg) {
  const slide = document.createElement("section");
  slide.className = "slide";
  if (slideCfg.textPosition === "bottom") slide.classList.add("slide--text-bottom");
  if (slideCfg.backdrop) slide.classList.add("slide--backdrop");
  slide.id = `slide-${slideCfg.number}`;

  const bg = document.createElement("img");
  bg.className = "slide__bg";
  bg.src = slideCfg.image;
  bg.alt = slideCfg.kicker || `Slide ${slideCfg.number}`;
  slide.appendChild(bg);

  const scrim = document.createElement("div");
  scrim.className = "slide__scrim";
  slide.appendChild(scrim);

  const content = document.createElement("div");
  content.className = "slide__content";

  if (slideCfg.kicker) {
    const kicker = document.createElement("div");
    kicker.className = "slide__kicker";
    kicker.textContent = slideCfg.kicker;
    content.appendChild(kicker);

    const rule = document.createElement("div");
    rule.className = "slide__kicker-rule";
    content.appendChild(rule);
  }

  const text = document.createElement("div");
  text.className = "slide__text";

  if (slideCfg.isCover) {
    const title = document.createElement("div");
    title.className = "slide__title";
    title.textContent = cfg.title;
    text.appendChild(title);

    const subtitle = document.createElement("div");
    subtitle.className = "slide__body";
    subtitle.textContent = cfg.subtitle;
    text.appendChild(subtitle);
  } else {
    const body = document.createElement("div");
    body.className = "slide__body";
    body.textContent = slideCfg.body || "";
    text.appendChild(body);
  }

  content.appendChild(text);

  const pagination = document.createElement("div");
  pagination.className = "slide__pagination";
  pagination.textContent = `${slideCfg.number} / 0${cfg.totalSlides}`;
  content.appendChild(pagination);

  const footer = document.createElement("div");
  footer.className = "slide__footer";
  const footerLabel = document.createElement("span");
  footerLabel.textContent = cfg.footerLabel;
  const dot = document.createElement("span");
  dot.className = "slide__footer-dot";
  const projectName = document.createElement("span");
  projectName.textContent = cfg.date ? `${cfg.projectName} · ${cfg.date}` : cfg.projectName;
  footer.appendChild(footerLabel);
  footer.appendChild(dot);
  footer.appendChild(projectName);
  content.appendChild(footer);

  slide.appendChild(content);
  return slide;
}

function showFatalError(message) {
  // Erro visível na tela — nunca falha silenciosamente.
  const box = document.createElement("div");
  box.style.cssText = [
    "position:fixed", "top:0", "left:0", "right:0",
    "background:#3a0d0d", "color:#ffbdbd",
    "font-family:monospace", "font-size:14px",
    "padding:16px 20px", "z-index:9999",
    "border-bottom:2px solid #ff6b6b",
    "white-space:pre-wrap",
  ].join(";");
  box.textContent = "[Sentinela RJ carousel] " + message;
  document.body.appendChild(box);
  console.error("[Sentinela RJ carousel]", message);
}

function renderCarousel() {
  console.log("BrandOS carousel render iniciado");

  const config = window.CAROUSEL_CONFIG;
  const container = document.getElementById("carousel-viewport");

  console.log("Config encontrada:", window.CAROUSEL_CONFIG);
  console.log("Container encontrado:", document.getElementById("carousel-viewport"));

  if (!container) {
    showFatalError(
      'Container "#carousel-viewport" não encontrado no HTML. ' +
      "Confirme se o template.html tem <div id=\"carousel-viewport\"></div> " +
      "e se render.js está sendo carregado DEPOIS desse div."
    );
    return;
  }

  if (!config) {
    showFatalError(
      "window.CAROUSEL_CONFIG não foi encontrado. Confirme se js/config.js " +
      "está sendo carregado ANTES de js/render.js no HTML, e se config.js " +
      "usa \"window.CAROUSEL_CONFIG = {...}\" (não \"const CAROUSEL_CONFIG = {...}\")."
    );
    return;
  }

  if (!Array.isArray(config.slides) || config.slides.length === 0) {
    showFatalError('CAROUSEL_CONFIG.slides está vazio ou não é um array.');
    return;
  }

  document.title = (config.title || "Carrossel").replace(/\n/g, " ");

  const meta = document.createElement("div");
  meta.className = "carousel-meta";
  meta.innerHTML = `<h1>${config.projectName || ""}</h1><p>${config.slides.length} slides · gerado a partir de config.js</p>`;
  container.appendChild(meta);

  config.slides.forEach((slideCfg) => {
    container.appendChild(buildSlide(config, slideCfg));
  });

  console.log(`Render concluído: ${config.slides.length} slides adicionados ao container.`);
}

document.addEventListener("DOMContentLoaded", renderCarousel);
