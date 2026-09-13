const $ = (id) => document.getElementById(id);
const API_BASE = window.SPACEWEAVE_API_BASE || "";
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

let selected = null;
const drop = $("drop");
const file = $("file");

function showError(message) {
  $("error").textContent = message;
  $("error").classList.remove("hidden");
}

function clearError() {
  $("error").classList.add("hidden");
  $("error").textContent = "";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  })[char]);
}

function safeUrl(value) {
  try {
    const url = new URL(String(value || ""), window.location.origin);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
  } catch {
    return "#";
  }
}

function setSelected(inputFiles) {
  const candidate = inputFiles?.[0];
  if (!candidate) return;

  if (!candidate.type.startsWith("image/")) {
    showError("Please upload a JPEG, PNG, or WebP image.");
    return;
  }
  if (candidate.size > MAX_UPLOAD_BYTES) {
    showError("Image exceeds the 10 MB limit.");
    return;
  }

  clearError();
  selected = candidate;
  $("empty").classList.add("hidden");
  const preview = $("preview");
  preview.src = URL.createObjectURL(candidate);
  preview.classList.remove("hidden");
}

drop.onclick = () => file.click();
file.onchange = () => setSelected(file.files);
drop.ondragover = (event) => {
  event.preventDefault();
  drop.classList.add("ring-2", "ring-indigo-400");
};
drop.ondragleave = () => drop.classList.remove("ring-2", "ring-indigo-400");
drop.ondrop = (event) => {
  event.preventDefault();
  drop.classList.remove("ring-2", "ring-indigo-400");
  setSelected(event.dataTransfer.files);
};

$("search").onclick = async () => {
  if (!selected) {
    showError("Upload a room image first.");
    return;
  }

  clearError();
  $("search").disabled = true;
  $("status").classList.remove("hidden");
  $("status").textContent = "Analyzing image and searching the vector index…";

  const form = new FormData();
  form.append("file", selected);
  for (const [id, key] of [
    ["query", "query"],
    ["category", "category"],
    ["room", "room_type"],
    ["budget", "max_budget"],
    ["aw", "available_width"],
    ["ad", "available_depth"],
    ["topk", "top_k"],
  ]) {
    const value = $(id).value.trim();
    if (value) form.append(key, value);
  }

  try {
    const response = await fetch(`${API_BASE}/api/v1/search`, {
      method: "POST",
      body: form,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Search failed.");
    render(data);
  } catch (error) {
    showError(error.message || "Search failed. Please try again.");
  } finally {
    $("search").disabled = false;
    $("status").classList.add("hidden");
  }
};

function render(data) {
  $("market").classList.remove("hidden");
  $("meta").textContent = `${data.metadata.result_count} results · ${data.metadata.candidate_count} vector candidates · ${data.metadata.model}`;

  const grid = $("grid");
  grid.innerHTML = "";

  for (const product of data.results || []) {
    const title = escapeHtml(product.title || "Untitled product");
    const source = escapeHtml(product.source || "Catalog");
    const category = escapeHtml(String(product.category || "").replaceAll("_", " "));
    const fitStatus = escapeHtml(product.fit_status || "unknown");
    const fitReason = escapeHtml(product.fit_reason || "");
    const imageUrl = safeUrl(product.image_url);
    const productUrl = safeUrl(product.product_url);
    const price = Number(product.price_inr);
    const priceText = Number.isFinite(price) ? `₹${price.toLocaleString("en-IN")}` : "Price unavailable";

    const card = document.createElement("article");
    card.className = "card bg-white border rounded-2xl overflow-hidden";
    card.innerHTML = `
      <img src="${imageUrl}" class="w-full h-48 object-cover" loading="lazy" alt="${title}">
      <div class="p-4">
        <div class="text-[11px] text-stone-500">${source} · ${category}</div>
        <h3 class="font-bold mt-1 line-clamp-2">${title}</h3>
        <div class="mt-2 text-lg font-black">${priceText}</div>
        <div class="mt-2 text-xs text-stone-500">${product.width_cm ?? "?"} × ${product.depth_cm ?? "?"} cm · ★ ${product.rating ?? "—"} (${product.review_count ?? 0})</div>
        <div class="mt-3 flex flex-wrap gap-1">
          <span class="px-2 py-1 rounded-full bg-indigo-50 text-indigo-700 text-[11px]">${Math.round(Number(product.final_score || 0) * 100)}% fit</span>
          <span class="px-2 py-1 rounded-full bg-stone-100 text-stone-600 text-[11px]">${fitStatus}</span>
        </div>
        <p class="mt-3 text-xs text-stone-500">${fitReason}</p>
        <a target="_blank" rel="noopener noreferrer" href="${productUrl}" class="mt-3 inline-block text-sm font-semibold text-indigo-600">View product →</a>
      </div>`;
    grid.appendChild(card);
  }
}
