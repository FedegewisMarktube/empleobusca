document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const queryRaw = (params.get('q') || '').trim();
  const query = queryRaw.toLowerCase();

  // ✅ ciudad opcional (ej: buenos_aires)
  const cityParam = (params.get('city') || '').trim().toLowerCase();

  const titulo = document.getElementById("titulo");
  const subtitulo = document.getElementById("subtitulo");
  const contenedor = document.getElementById("resultados");

  // ✅ SIEMPRE escribimos en el contenedor visible
  const detailContainer = document.getElementById("detalle_contenido");

  // ✅ baseDir robusto: carpeta actual (termina con /)
  const baseDir = window.location.pathname.replace(/\/[^\/]*$/, "/");

  if (!titulo || !subtitulo || !contenedor || !detailContainer) {
    console.error("Faltan elementos del DOM (titulo/subtitulo/resultados/detalle_contenido).");
    return;
  }

  if (!query) {
    titulo.innerText = "Búsqueda global";
    subtitulo.innerText = "Volvé al Home e ingresá un término.";
    return;
  }

  titulo.innerText = `Resultados para: "${queryRaw}"`;
  subtitulo.innerText = "Buscando en todas las ciudades y páginas…";

  const TODAS_CIUDADES = [
  { nombre: 'Buenos Aires', slug: 'buenos_aires' },
  { nombre: 'Córdoba', slug: 'cordoba' },
  { nombre: 'Mendoza', slug: 'mendoza' }
  ];

  // ✅ si viene city=..., filtramos
  const ciudades = cityParam
    ? TODAS_CIUDADES.filter(c => c.slug === cityParam)
    : TODAS_CIUDADES;

  const MAX_PAGINAS = 50;
  let totalEncontrados = 0;

  /* ===== helpers ===== */
  function escapeHtml(str) {
    return (str || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function txt(el) {
    return (el && el.textContent ? el.textContent : "").trim();
  }

  function buildDescripcionHtml(descripcionHtml) {
    if (!descripcionHtml) return "";

    const tmp = document.createElement("div");
    tmp.innerHTML = descripcionHtml;

    const lines = Array.from(tmp.querySelectorAll("p"))
      .map((p) => (p.textContent || "").trim())
      .filter((p) => p.length > 0);

    let html = "";
    for (const line of lines) {
      if (/^\s*[-*]\s+/.test(line)) {
        const t = line.replace(/^\s*[-*]\s+/, "");
        html += `<p style="margin:0 0 8px 0;">• ${escapeHtml(t)}</p>`;
      } else {
        html += `<p style="margin:0 0 10px 0;">${escapeHtml(line)}</p>`;
      }
    }
    return html;
  }

  function extraerData(oferta) {
    const t =
      txt(oferta.querySelector("h2 a")) ||
      txt(oferta.querySelector("h2")) ||
      "Oferta";

    const ps = Array.from(oferta.querySelectorAll("p"))
      .map((p) => txt(p))
      .filter(Boolean);

    const empresa = ps[0] || "";
    const ubicacion = ps[1] || "";
    const fecha = ps[2] || "";

    const descDiv = oferta.querySelector(".descripcion_scrapeada");
    const descripcionHtml = descDiv ? (descDiv.innerHTML || "").trim() : "";

    return { titulo: t, empresa, ubicacion, fecha, descripcionHtml };
  }

  function renderCard(data) {
    const payload = encodeURIComponent(JSON.stringify(data));

    return `
      <article class="box_offer" data-detail="${payload}">
        <h2 class="fs18 fwB prB">
          <a class="fc_base t_ellipsis" href="#" data-no-nav="1">${escapeHtml(data.titulo)}</a>
        </h2>

        <p class="dFlex vm_fx fs16 fc_base mt5">
          <span class="t_ellipsis">${escapeHtml(data.empresa)}</span>
        </p>

        <p class="fs16 fc_base mt5">
          <span class="mr10">${escapeHtml(data.ubicacion)}</span>
        </p>

        <p class="fs13 fc_aux mt15">
          ${escapeHtml(data.fecha)}
        </p>
      </article>
    `;
  }

  function renderDetalle(data) {
    const desc = buildDescripcionHtml(data.descripcionHtml);

    detalle_contenido.innerHTML = `
      <p class="fs28 fwB mb10">${escapeHtml(data.titulo)}</p>

      <p class="fs22 fwB">${escapeHtml(data.empresa)}</p>
      <p class="mb15">${escapeHtml(data.ubicacion)}</p>

      <span class="b_primary big" role="button" tabindex="0">Postularme</span>

      <div class="mt15">
        ${desc ? desc : `<p class="fc_aux">Sin descripción disponible.</p>`}
      </div>
    `;
  }

  /* ===== Click delegado: abrir panel + marcar sel ===== */
  contenedor.addEventListener("click", (e) => {
    const card = e.target.closest(".box_offer");
    if (!card) return;

    const anyLink = e.target.closest("a");
    if (anyLink) {
      e.preventDefault();
      e.stopPropagation();
    }

    if (card.classList.contains("sel")) return;

    contenedor
      .querySelectorAll(".box_offer.sel")
      .forEach((x) => x.classList.remove("sel"));
    card.classList.add("sel");

    let data;
    try {
      data = JSON.parse(decodeURIComponent(card.getAttribute("data-detail") || "{}"));
    } catch {
      data = null;
    }

    if (!data) {
      detailContainer.innerHTML = `<div class="nores">No se pudo cargar el detalle.</div>`;
      return;
    }

    renderDetalle(data);
  });

  /* ===== Buscar ===== */
  async function buscarCiudad(ciudad) {
    for (let pagina = 1; pagina <= MAX_PAGINAS; pagina++) {
      // ✅ URL robusta basada en la carpeta actual
      const url = `${baseDir}${ciudad.slug}/${ciudad.slug}_p${pagina}.html`;

      let res;
      try {
        res = await fetch(url, { cache: "no-store" });
      } catch {
        break;
      }

      if (!res.ok) break;

      const html = await res.text();
      const temp = document.createElement("div");
      temp.innerHTML = html;

      const ofertas = temp.querySelectorAll(".box_offer");
      if (ofertas.length === 0) break;

      ofertas.forEach((oferta) => {
        const texto = (oferta.innerText || "").toLowerCase();
        if (!texto.includes(query)) return;

        const data = extraerData(oferta);
        contenedor.insertAdjacentHTML("beforeend", renderCard(data));
        totalEncontrados++;
      });
    }
  }

  async function buscarGlobal() {
    for (const ciudad of ciudades) {
      await buscarCiudad(ciudad);
    }

    if (totalEncontrados === 0) {
      contenedor.innerHTML = '<div class="nores">No se encontraron resultados.</div>';
      detailContainer.innerHTML = "No hay resultados para mostrar.";
    }

    subtitulo.innerText = cityParam
    ? 'Buscando solo en Buenos Aires…'
    : 'Buscando en todas las ciudades y páginas…';

    // ✅ auto-seleccionar primera oferta
    const first = contenedor.querySelector(".box_offer");
    if (first) first.click();
  }

  buscarGlobal();
});
