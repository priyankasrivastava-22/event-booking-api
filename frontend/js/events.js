console.log("JS loaded");

const API_URL = (window.API_BASE_URL || ((["localhost", "127.0.0.1"].includes(window.location.hostname)) ? "http://127.0.0.1:8000" : window.location.origin)).replace(/\/$/, "") + "/api";

// ---------------- CATEGORY IMAGE MAPPING ----------------
function getCategoryImage(category) {
    const cat = category ? category.toLowerCase() : "";
    if (cat.includes('music') || cat.includes('concert')) return 'https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?auto=format&fit=crop&w=400';
    if (cat.includes('tech') || cat.includes('conference')) return 'https://images.unsplash.com/photo-1505373877841-8d25f7d46678?auto=format&fit=crop&w=400';
    if (cat.includes('food')) return 'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=400';
    return 'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=400';
}

// ---------------- GET USER FROM TOKEN ----------------
function getUserFromToken() {
    const token = localStorage.getItem("token");
    if (!token) return null;
    try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        return payload;
    } catch (e) {
        return null;
    }
}

// ---------------- ADMIN BUTTON CONTROL ----------------
function setupAdminUI() {
    const user = getUserFromToken();
    if (!user || user.role !== "admin") return;

    const adminLink = document.getElementById("adminLink");
    if (adminLink) {
        adminLink.style.display = "flex";
    }
}

// ---------------- AUTH CHECK ----------------
function checkAuth() {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        return null;
    }
    return token;
}

// ---------------- LOAD CATEGORIES ----------------
async function loadCategories() {
    const token = localStorage.getItem("token");
    try {
        const res = await fetch(`${API_URL}/engagement/categories`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const categories = await res.json();
        const dropdown = document.getElementById("categoryFilter");
        if (!dropdown) return;

        dropdown.innerHTML = `<option value="">All Categories</option>`;

        // Use a Set to ensure unique names in the dropdown
        const uniqueNames = [...new Set(categories.map(cat => cat.name))];

        uniqueNames.forEach(name => {
            if(name) {
                const option = document.createElement("option");
                option.value = name;
                option.textContent = name;
                dropdown.appendChild(option);
            }
        });
    } catch (err) {
        console.error("Category load error:", err);
    }
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

// ---------------- LOAD EVENTS & APPLY FILTERS ----------------
async function loadEvents() {
    const token = localStorage.getItem("token");

    const category =
        document.getElementById("categoryFilter")?.value || "";

    const search =
        document.getElementById("searchInput")?.value.trim() || "";

    let url = `${API_URL}/events/?limit=16`;

    // Build query parameters
    const params = new URLSearchParams();

    if (search) {
        params.append("title", search);
    }

    if (category) {
        params.append("category", category);
    }

    if (params.toString()) {
        url += `&${params.toString()}`;
    }

    try {
        console.log("Loading events from:", url);

        const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
        if (!res.ok) throw new Error(`Unable to load events (${res.status})`);

        console.log("Events API status:", res.status);

        const data = await res.json();

        console.log("Events data:", data);

        const container =
            document.getElementById("eventsContainer");

        if (!container) return;

        container.innerHTML = "";

        if (!Array.isArray(data) || data.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <h5 class="text-white">
                        No events found for "${escapeHtml(category || search)}"
                    </h5>
                </div>
            `;
            return;
        }

        data.forEach(event => {
            const imageUrl = event.image_url || getCategoryImage(event.category);
            const card = document.createElement("div");
            card.className = "col";
            card.innerHTML = `
                <div class="card h-100 shadow-sm border-secondary bg-dark text-white">
                    <img class="card-img-top" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(event.title || 'Event')}" style="height:120px;object-fit:cover">
                    <div class="card-body p-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="card-title mb-1 text-truncate" style="font-size:.9rem">${escapeHtml(event.title || 'Event')}</h6>
                            <button class="btn btn-link btn-sm wishlist-toggle" type="button" aria-label="Toggle wishlist"><i class="bi ${isInWishlist(event.id) ? 'bi-heart-fill text-danger' : 'bi-heart'}"></i></button>
                        </div>
                        <p class="card-text small text-muted mb-2"><i class="bi bi-geo-alt"></i> ${escapeHtml(event.location || 'Venue TBA')}</p>
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span class="fw-bold text-primary">₹${Number(event.price || 0).toLocaleString('en-IN')}</span>
                            <span class="badge bg-secondary">${escapeHtml(event.category || 'Event')}</span>
                        </div>
                        <button class="btn btn-primary btn-sm w-100 view-details" type="button">Details</button>
                    </div>
                </div>`;
            card.querySelector('.view-details').addEventListener('click', () => viewEvent(event.id, imageUrl));
            card.querySelector('.wishlist-toggle').addEventListener('click', e => toggleWishlist({...event, image_url:imageUrl}, e.currentTarget.querySelector('i')));
            container.appendChild(card);
        });

    } catch (err) {
        console.error("Events loading error:", err);
        const container = document.getElementById("eventsContainer");
        if (container) {
            container.innerHTML = `<div class="col-12 alert alert-warning" role="alert">Unable to load events. Check your API connection. <button class="btn btn-sm btn-outline-dark" type="button" id="retryEvents">Retry</button></div>`;
            document.getElementById("retryEvents")?.addEventListener("click", loadEvents);
        }
    }
}

// ---------------- NOTIFICATION FUNCTIONS ----------------
async function loadNotificationCount() {
    const token = localStorage.getItem("token");
    if (!token) return;
    try {
        const res = await fetch(`${API_URL}/engagement/notifications/my`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        const badge = document.getElementById("notifCount");
        if (!badge) return;
        const count = Array.isArray(data) ? data.length : 0;
        badge.innerText = count;
        badge.style.display = count === 0 ? "none" : "inline-block";
    } catch (err) { console.error(err); }
}

// ---------------- USER AVATAR ----------------
async function loadUserAvatar() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/profile/`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        const avatarBtn = document.getElementById("userAvatarBtn");
        if (!avatarBtn) return;

        if (data.profile_image) {
            avatarBtn.innerHTML = `
                <img src="${data.profile_image}"
                     style="width:36px; height:36px; border-radius:50%; object-fit:cover; border: 2px solid #22d3ee;">`;
        } else {
            const letter = (data.username || "U")[0].toUpperCase();
            avatarBtn.innerHTML = `
                <div style="
                    width:36px; height:36px; border-radius:50%;
                    background: linear-gradient(135deg, #22d3ee, #2563eb);
                    display:flex; align-items:center; justify-content:center;
                    font-weight:700; font-size:1rem; color:#04111f;">
                    ${letter}
                </div>`;
        }
    } catch {}
}

// ---------------- USER LOGOUT ----------------
function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

// ---------------- EVENT DETAILS NAVIGATION ----------------
function viewEvent(id, img) {
     window.location.href = `event-details.html?id=${id}&img=${encodeURIComponent(img)}`;

}

// ---------------- PAGE INITIALIZATION ----------------
document.addEventListener("DOMContentLoaded", () => {
    setupAdminUI();
    loadCategories();
    loadEvents();
    loadNotificationCount();
    loadUserAvatar();
    setInterval(loadNotificationCount, 60000);

    // Profile Name update
    const user = getUserFromToken();
    if (user && document.getElementById("nav-username")) {
        document.getElementById("nav-username").innerText = user.sub || "User";
    }

    document.getElementById("categoryFilter")?.addEventListener("change", loadEvents);
    document.getElementById("searchInput")?.addEventListener("input", loadEvents);
});

// ---------------- CATEGORY CARD FILTERING ----------------
document.querySelectorAll(".category-card").forEach(card => {

    card.addEventListener("click", () => {

        document.querySelectorAll(".category-card")
            .forEach(c => c.classList.remove("active"));

        card.classList.add("active");

        const selectedCategory =
            card.dataset.category;

        document.getElementById("categoryFilter").value =
            selectedCategory;

        loadEvents();
    });

});

// ---------------- WISHLIST ----------------

function toggleWishlist(event, icon) {

    let wishlist = safeWishlist();

    const exists =
        wishlist.some(item => item.id === event.id);

    if (exists) {

        wishlist =
            wishlist.filter(
                item => item.id !== event.id
            );

        icon.classList.remove(
            "bi-heart-fill",
            "text-danger"
        );

        icon.classList.add(
            "bi-heart"
        );

    } else {

        wishlist.push(event);

        icon.classList.remove(
            "bi-heart"
        );

        icon.classList.add(
            "bi-heart-fill",
            "text-danger"
        );
    }

    localStorage.setItem(
        "wishlist",
        JSON.stringify(wishlist)
    );
}

function isInWishlist(eventId) {

    const wishlist = safeWishlist();

    return wishlist.some(
        item => item.id === eventId
    );
}
function safeWishlist() {
    try { const list = JSON.parse(localStorage.getItem("wishlist") || "[]"); return Array.isArray(list) ? list : []; }
    catch { localStorage.removeItem("wishlist"); return []; }
}
