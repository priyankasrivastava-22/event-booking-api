console.log("JS loaded");

const API_URL = "https://event-booking-api-gnww.onrender.com/api";

// --- Helper: Dynamic Image Generator ---
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

    const navbar = document.querySelector(".navbar");
    if (!navbar) return;

    const btn = document.createElement("button");
    btn.className = "btn btn-outline-light btn-sm ms-2";
    btn.innerText = "Admin";
    btn.onclick = () => { window.location.href = "admin.html"; };
    navbar.appendChild(btn);
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

// ---------------- LOAD EVENTS (Fixed Logic) ----------------
async function loadEvents() {
    const token = localStorage.getItem("token");
    if (!token) return;

    const category = document.getElementById("categoryFilter")?.value || "";
    const search = document.getElementById("searchInput")?.value.trim() || "";

    // IMPORTANT: Path is just /events, parameters handle the filtering
    let url = `${API_URL}/events/events?limit=16`;

    // FIX: Only use the search endpoint if a category is selected or text is typed
//    if (category !== "" || search !== "") {
        const params = new URLSearchParams();
        if (search) params.append("title", search);
        if (category) params.append("category", category);

        if (params.toString()) {
        url += `&${params.toString()}`;
    }

    try {
        const res = await fetch(url, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();

        const container = document.getElementById("eventsContainer");
        if (!container) return;
        container.innerHTML = "";

        if (!data || data.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <h5 class="text-white">No events found for "${category || search}"</h5>
                </div>`;
            return;
        }

        data.forEach(event => {
        const imageUrl = getCategoryImage(event.category);
          container.innerHTML += `
          <div class="col">
            <div class="card h-100 shadow-sm border-secondary bg-dark text-white">
                <img src="${imageUrl}" class="card-img-top" style="height: 120px; object-fit: cover;">
                <div class="card-body p-2">
                    <h6 class="card-title mb-1 text-truncate" style="font-size: 0.9rem;">${event.title}</h6>
                    <p class="card-text small text-muted mb-2" style="font-size: 0.75rem;">
                        <i class="bi bi-geo-alt"></i> ${event.location}
                    </p>
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="fw-bold text-primary" style="font-size: 0.85rem;">₹${event.price}</span>
                        <span class="badge bg-secondary" style="font-size: 0.6rem;">${event.category}</span>
                    </div>
                    <button class="btn btn-primary btn-sm w-100" style="font-size: 0.75rem;" onclick="viewEvent(${event.id}, '${imageUrl}')">Details</button>
                </div>
            </div>
        </div>`;
        });

       } catch (err) {
        console.error("Filtering error:", err);
   }
 }

// ---------------- NOTIFICATION & LOGOUT ----------------
async function loadNotificationCount() {
    const token = localStorage.getItem("token");
    if (!token) return;
    try {
        const res = await fetch(`${API_URL}/engagement/my-notifications`, {
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

function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

function viewEvent(id, img) {
     window.location.href = `event-details.html?id=${id}&img=${encodeURIComponent(img)}`;

}

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", () => {
    setupAdminUI();
    loadCategories();
    loadEvents();
    loadNotificationCount();
    setInterval(loadNotificationCount, 5000);

    // Profile Name update
    const user = getUserFromToken();
    if (user && document.getElementById("nav-username")) {
        document.getElementById("nav-username").innerText = user.sub || "User";
    }

    document.getElementById("categoryFilter")?.addEventListener("change", loadEvents);
    document.getElementById("searchInput")?.addEventListener("input", loadEvents);
});