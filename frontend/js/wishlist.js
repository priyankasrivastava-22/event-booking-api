"use strict";
/* Device-local favorites for the frontend demo. Cross-device synchronization requires a future API. */
const escapeWishlist = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function storedWishlist() {
    try { const values = JSON.parse(localStorage.getItem("wishlist") || "[]"); return Array.isArray(values) ? values : []; }
    catch { localStorage.removeItem("wishlist");return []; }
}
function loadWishlist() {
    const container = document.getElementById("wishlistContainer");
    const search = (document.getElementById("wishlistSearchInput")?.value || "").trim().toLowerCase();
    const events = storedWishlist().filter(item => String(item.title || "").toLowerCase().includes(search));
    if (!events.length) {
        container.innerHTML = `<div class="col-12 text-center py-5"><h4>${search ? "No matching saved events" : "No saved events yet"}</h4><a href="events.html" class="btn btn-primary mt-3">Explore events</a></div>`;
        return;
    }
    container.innerHTML = events.map(event => `<div class="col mb-3"><article class="wishlist-card h-100">
      <img class="wishlist-image" src="${escapeWishlist(event.image_url || "../images/logos/logo.png")}" alt="${escapeWishlist(event.title || "Event")}">
      <div class="wishlist-content"><div class="d-flex justify-content-between align-items-center"><h5>${escapeWishlist(event.title || "Event")}</h5>
      <button class="remove-btn" type="button" aria-label="Remove saved event" data-remove="${Number(event.id)}"><i class="bi bi-heart-fill"></i></button></div>
      <p><i class="bi bi-geo-alt"></i> ${escapeWishlist(event.location || "Venue TBA")}</p>
      <p>${escapeWishlist(event.category || "Event")}</p><h6>₹${Number(event.price || 0).toLocaleString("en-IN")}</h6>
      <div class="action-buttons"><a class="btn btn-outline-light" href="event-details.html?id=${Number(event.id)}">Details</a>
      <a class="btn btn-primary" href="event-details.html?id=${Number(event.id)}">Choose tickets</a></div></div></article></div>`).join("");
    container.querySelectorAll("[data-remove]").forEach(button => button.addEventListener("click", () => {
        const id = Number(button.dataset.remove);
        localStorage.setItem("wishlist", JSON.stringify(storedWishlist().filter(event => Number(event.id) !== id)));
        loadWishlist();
    }));
}
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("backBtn")?.addEventListener("click", () => location.href = "events.html");
    document.getElementById("wishlistSearchInput")?.addEventListener("input", loadWishlist);
    loadWishlist();
});
