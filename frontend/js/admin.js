//const API_URL = "http://127.0.0.1:8000";
//
//// ---------------- AUTH ----------------
//function getToken() {
//    const token = localStorage.getItem("token");
//    if (!token) {
//        alert("Login required");
//        window.location.href = "login.html";
//        return null;
//    }
//    return token;
//}
//
//// ---------------- ADMIN PROTECTION (ADDED) ----------------
//// This ensures ONLY admin can access this page
//function getUserFromToken() {
//    const token = localStorage.getItem("token");
//    if (!token) return null;
//
//    try {
//        return JSON.parse(atob(token.split(".")[1]));
//    } catch {
//        return null;
//    }
//}
//
//function protectAdminPage() {
//    const user = getUserFromToken();
//
//    if (!user || user.role !== "admin") {
//        alert("Access denied. Admins only.");
//        window.location.href = "events.html";
//    }
//}
//
//// ---------------- LOAD CATEGORIES ----------------
//async function loadCategories() {
//    const token = getToken();
//    if (!token) return;
//
//    const res = await fetch(`${API_URL}/categories`, {
//        headers: { "Authorization": `Bearer ${token}` }
//    });
//
//    const data = await res.json();
//
//    const dropdown = document.getElementById("categorySelect");
//    dropdown.innerHTML = "";
//
//    data.forEach(cat => {
//        const option = document.createElement("option");
//        option.value = cat.id;
//        option.textContent = cat.name;
//        dropdown.appendChild(option);
//    });
//}
//
//// ---------------- CREATE CATEGORY ----------------
//async function createCategory() {
//    const token = getToken();
//    if (!token) return;
//
//    const name = document.getElementById("categoryName").value;
//
//    const res = await fetch(`${API_URL}/admin/categories`, {
//        method: "POST",
//        headers: {
//            "Content-Type": "application/json",
//            "Authorization": `Bearer ${token}`
//        },
//        body: JSON.stringify({ name })
//    });
//
//    const data = await res.json();
//
//    if (res.ok) {
//        alert("Category created");
//        loadCategories();
//    } else {
//        alert(data.detail);
//    }
//}
//
//// ---------------- CREATE EVENT ----------------
//async function createEvent() {
//    const token = getToken();
//    if (!token) return;
//
//    const body = {
//        title: document.getElementById("title").value,
//        description: document.getElementById("description").value,
//        location: document.getElementById("location").value,
//        price: parseInt(document.getElementById("price").value),
//        total_seats: parseInt(document.getElementById("seats").value),
//        available_seats: parseInt(document.getElementById("seats").value),
//        category_id: parseInt(document.getElementById("categorySelect").value),
//        date_time: document.getElementById("date").value
//    };
//
//    const res = await fetch(`${API_URL}/events`, {
//        method: "POST",
//        headers: {
//            "Content-Type": "application/json",
//            "Authorization": `Bearer ${token}`
//        },
//        body: JSON.stringify(body)
//    });
//
//    const data = await res.json();
//
//    if (res.ok) {
//        alert("Event created");
//    } else {
//        alert(data.detail);
//    }
//}
//
//// ---------------- SEND NOTIFICATION ----------------
//async function sendNotification() {
//    const token = getToken();
//    if (!token) return;
//
//    const message = document.getElementById("message").value;
//    const user_name = document.getElementById("username").value || null;
//
//    const res = await fetch(`${API_URL}/admin/notify`, {
//        method: "POST",
//        headers: {
//            "Content-Type": "application/json",
//            "Authorization": `Bearer ${token}`
//        },
//        body: JSON.stringify({ message, user_name })
//    });
//
//    const data = await res.json();
//
//    if (res.ok) {
//        alert("Notification sent");
//    } else {
//        alert(data.detail);
//    }
//}
//
//// ---------------- INIT ----------------
//document.addEventListener("DOMContentLoaded", () => {
//    protectAdminPage();
//    loadCategories();
//});


//
//const API_URL = "http://127.0.0.1:8000";
//
//// ---------------- AUTH ----------------
//function getToken() {
//    const token = localStorage.getItem("token");
//    if (!token) {
//        alert("Login required");
//        window.location.href = "login.html";
//        return null;
//    }
//    return token;
//}
//
//function getUserFromToken() {
//    const token = localStorage.getItem("token");
//    if (!token) return null;
//    try {
//        return JSON.parse(atob(token.split(".")[1]));
//    } catch {
//        return null;
//    }
//}
//
//function protectAdminPage() {
//    const user = getUserFromToken();
//    if (!user || user.role !== "admin") {
//        alert("Access denied. Admins only.");
//        window.location.href = "events.html";
//    }
//}
//
//// ---------------- DASHBOARD NAVIGATION (NEW) ----------------
//document.addEventListener("DOMContentLoaded", () => {
//    protectAdminPage();
//
//    // Set up click listeners for sidebar links
//    document.querySelectorAll('.admin-nav').forEach(link => {
//        link.addEventListener('click', (e) => {
//            e.preventDefault();
//            document.querySelectorAll('.admin-nav').forEach(l => l.classList.remove('active'));
//            link.classList.add('active');
//
//            const section = link.getAttribute('data-section');
//            showSection(section);
//        });
//    });
//
//    // Default view
//    showSection('stats');
//});
//
//async function showSection(section) {
//    const mainView = document.getElementById('admin-main-view');
//    const title = document.getElementById('section-title');
//    const actions = document.getElementById('header-actions');
//
//    mainView.innerHTML = `<div class="text-center mt-5"><div class="spinner-border text-primary"></div></div>`;
//    actions.innerHTML = "";
//
//    if (section === 'stats') {
//        title.innerText = "Dashboard Overview";
//        mainView.innerHTML = `
//            <div class="row g-4">
//                <div class="col-md-3"><div class="card p-4 text-white bg-primary"><h6>Total Users</h6><h3>--</h3></div></div>
//                <div class="col-md-3"><div class="card p-4 text-white bg-success"><h6>Active Events</h6><h3>--</h3></div></div>
//                <div class="col-md-3"><div class="card p-4 text-white bg-info"><h6>Bookings</h6><h3>--</h3></div></div>
//                <div class="col-md-3"><div class="card p-4 text-white bg-warning"><h6>Categories</h6><h3>--</h3></div></div>
//            </div>
//            <div class="mt-4 p-4 card">
//                <h5>Recent Activity</h5>
//                <p class="text-muted">Welcome to the management console. Select a tab from the sidebar to manage your application.</p>
//            </div>`;
//    }
//    else if (section === 'users') {
//        title.innerText = "User Management";
//        const users = await fetchAdminData("/admin/users");
//        mainView.innerHTML = renderUserTable(users);
//    }
//    else if (section === 'events') {
//        title.innerText = "Event Management";
//        actions.innerHTML = `<button class="btn btn-primary btn-sm" onclick="openCreateEventModal()">+ Create Event</button>`;
//        const events = await fetchAdminData("/events");
//        mainView.innerHTML = renderEventAdminGrid(events);
//    }
//    else if (section === 'bookings') {
//        title.innerText = "All Bookings";
//        const bookings = await fetchAdminData("/admin/bookings");
//        mainView.innerHTML = renderBookingTable(bookings);
//    }
//}
//
//// ---------------- TABLE RENDERERS (NEW) ----------------
//
//function renderUserTable(users) {
//    return `
//    <div class="card bg-dark border-secondary">
//        <table class="table table-dark table-hover mb-0">
//            <thead><tr><th>ID</th><th>Username</th><th>Role</th><th>Actions</th></tr></thead>
//            <tbody>
//                ${users.map(u => `
//                <tr>
//                    <td>${u.id}</td>
//                    <td>${u.username}</td>
//                    <td><span class="badge bg-secondary">${u.role}</span></td>
//                    <td><button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${u.id})">Delete</button></td>
//                </tr>`).join('')}
//            </tbody>
//        </table>
//    </div>`;
//}
//
//function renderBookingTable(bookings) {
//    return `
//    <div class="card bg-dark border-secondary">
//        <table class="table table-dark table-hover mb-0">
//            <thead><tr><th>ID</th><th>User</th><th>Event</th><th>Date</th><th>Action</th></tr></thead>
//            <tbody>
//                ${bookings.map(b => `
//                <tr>
//                    <td>${b.id}</td>
//                    <td>${b.user_name || 'User '+b.user_id}</td>
//                    <td>${b.event_title || 'Event '+b.event_id}</td>
//                    <td>${new Date().toLocaleDateString()}</td>
//                    <td><button class="btn btn-sm btn-outline-danger" onclick="deleteBooking(${b.id})">Cancel</button></td>
//                </tr>`).join('')}
//            </tbody>
//        </table>
//    </div>`;
//}
//
//// Function to render the specific Table UI
//function renderEventAdminTable(events) {
//    // Limit to 10 events per page logic (assuming current page is handled)
//    const displayEvents = events.slice(0, 10);
//    document.getElementById('total-count').innerText = events.length;
//
//    return `
//    <table class="table table-dark table-hover align-middle mb-0" style="font-size: 0.9rem;">
//        <thead class="table-light text-dark">
//            <tr>
//                <th class="ps-3">#</th>
//                <th>Event Name</th>
//                <th>Location</th>
//                <th>Category</th>
//                <th>Price</th>
//                <th>Seats</th>
//                <th>Date & Time</th>
//                <th class="text-center">Actions</th>
//            </tr>
//        </thead>
//        <tbody>
//            ${displayEvents.map((e, index) => `
//            <tr>
//                <td class="ps-3 text-muted">${index + 1}</td>
//                <td class="fw-bold">${e.title}</td>
//                <td><i class="bi bi-geo-alt small text-primary me-1"></i>${e.location}</td>
//                <td><span class="badge bg-secondary opacity-75">${e.category || 'General'}</span></td>
//                <td class="text-info fw-bold">₹${e.price}</td>
//                <td>${e.available_seats}/${e.total_seats}</td>
//                <td class="small text-muted">${e.date_time}</td>
//                <td class="text-center">
//                    <div class="btn-group">
//                        <button class="btn btn-sm btn-outline-warning border-0" onclick="editEvent(${e.id})">
//                            <i class="bi bi-pencil-square"></i>
//                        </button>
//                        <button class="btn btn-sm btn-outline-danger border-0" onclick="deleteEvent(${e.id})">
//                            <i class="bi bi-trash"></i>
//                        </button>
//                    </div>
//                </td>
//            </tr>`).join('')}
//        </tbody>
//    </table>`;
//}
//
//// Update your showSection function to call this
//async function showSection(section) {
//    // ... same logic as before ...
//    if (section === 'events') {
//        const events = await fetchAdminData("/events");
//        const mainView = document.getElementById('admin-main-view');
//        mainView.innerHTML = renderEventAdminTable(events);
//    }
//}
//
//// ---------------- HELPER FETCH (NEW) ----------------
//async function fetchAdminData(endpoint) {
//    const token = getToken();
//    const res = await fetch(`${API_URL}${endpoint}`, {
//        headers: { "Authorization": `Bearer ${token}` }
//    });
//    return await res.json();
//}
//
//// ---------------- EXISTING LOGIC (PRESERVED) ----------------
//
//async function loadCategories() {
//    const token = getToken();
//    if (!token) return;
//    const res = await fetch(`${API_URL}/categories`, {
//        headers: { "Authorization": `Bearer ${token}` }
//    });
//    const data = await res.json();
//    const dropdown = document.getElementById("categorySelect");
//    if (dropdown) {
//        dropdown.innerHTML = "";
//        data.forEach(cat => {
//            const option = document.createElement("option");
//            option.value = cat.id;
//            option.textContent = cat.name;
//            dropdown.appendChild(option);
//        });
//    }
//}
//
//async function createCategory() {
//    const token = getToken();
//    const name = document.getElementById("categoryName").value;
//    const res = await fetch(`${API_URL}/admin/categories`, {
//        method: "POST",
//        headers: {
//            "Content-Type": "application/json",
//            "Authorization": `Bearer ${token}`
//        },
//        body: JSON.stringify({ name })
//    });
//    if (res.ok) { alert("Category created"); loadCategories(); }
//}
//
//async function createEvent() {
//    const token = getToken();
//    const body = {
//        title: document.getElementById("title").value,
//        description: document.getElementById("description").value,
//        location: document.getElementById("location").value,
//        price: parseInt(document.getElementById("price").value),
//        total_seats: parseInt(document.getElementById("seats").value),
//        available_seats: parseInt(document.getElementById("seats").value),
//        category_id: parseInt(document.getElementById("categorySelect").value),
//        date_time: document.getElementById("date").value
//    };
//    const res = await fetch(`${API_URL}/events`, {
//        method: "POST",
//        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
//        body: JSON.stringify(body)
//    });
//    if (res.ok) alert("Event created");
//}
//
//async function sendNotification() {
//    const token = getToken();
//    const message = document.getElementById("message").value;
//    const user_name = document.getElementById("username").value || null;
//    const res = await fetch(`${API_URL}/admin/notify`, {
//        method: "POST",
//        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
//        body: JSON.stringify({ message, user_name })
//    });
//    if (res.ok) alert("Notification sent");
//}

const API_URL =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:8000/api"
        : "https://event-booking-api-gnww.onrender.com/api";

let currentSection = "stats";

/* ===================================================
   PERFORMANCE CACHE + STATE
=================================================== */
const sectionCache = {};
let loadingSection = false;

/* ===================================================
   AUTH
=================================================== */
function getToken() {
    const token = localStorage.getItem("token");

    if (!token) {
        alert("Login required");
        window.location.href = "login.html";
        return null;
    }

    return token;
}

function getUserFromToken() {
    const token = localStorage.getItem("token");
    if (!token) return null;

    try {
        return JSON.parse(atob(token.split(".")[1]));
    } catch {
        return null;
    }
}

function protectAdminPage() {
    const user = getUserFromToken();

    if (!user || user.role !== "admin") {
        alert("Access denied. Admins only.");
        window.location.href = "events.html";
    }
}

/* ===================================================
   INIT
=================================================== */
document.addEventListener("DOMContentLoaded", () => {
    protectAdminPage();

    document.querySelectorAll(".admin-nav").forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();

            if (loadingSection) return;

            document.querySelectorAll(".admin-nav")
                .forEach(l => l.classList.remove("active"));

            link.classList.add("active");

            const section = link.dataset.section;
            showSection(section);
        });
    });

    bindSearch();
    showSection("stats");
});

/* ===================================================
   HELPERS
=================================================== */
function showLoader() {
    document.getElementById("admin-main-view").innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-light"></div>
            <div class="mt-2 text-muted small">Loading...</div>
        </div>
    `;
}

function setHeader(titleText, actionsHTML = "") {
    document.getElementById("section-title").innerText = titleText;
    document.getElementById("header-actions").innerHTML = actionsHTML;
}

function renderMain(html) {
    document.getElementById("admin-main-view").innerHTML = html;
}

/* ===================================================
   MAIN SECTION HANDLER
=================================================== */
async function showSection(section, forceRefresh = false) {
    currentSection = section;
    loadingSection = true;

    if (!forceRefresh && sectionCache[section]) {
        renderMain(sectionCache[section]);
        setTitleBySection(section);
        loadingSection = false;

        if (section === "analytics") renderAnalyticsCharts();
        return;
    }

    showLoader();

    try {
        if (section === "stats") {
            setHeader("Analytics Dashboard");

            const stats = await fetchAdminData("/analytics/stats");

            const html = `
                <div class="row g-4">
                    <div class="col-md-3">
                        <div class="card p-4 text-white bg-primary">
                            <h6>Total Users</h6>
                            <h3>${stats.total_users}</h3>
                        </div>
                    </div>

                    <div class="col-md-3">
                        <div class="card p-4 text-white bg-success">
                            <h6>Active Events</h6>
                            <h3>${stats.total_events}</h3>
                        </div>
                    </div>

                    <div class="col-md-3">
                        <div class="card p-4 text-white bg-info">
                            <h6>Bookings</h6>
                            <h3>${stats.total_bookings}</h3>
                        </div>
                    </div>

                    <div class="col-md-3">
                        <div class="card p-4 text-white bg-warning">
                            <h6>Revenue</h6>
                            <h3>₹${stats.revenue}</h3>
                        </div>
                    </div>
                </div>

                <div class="card p-4 mt-4">
                    <h5>Recent Activity</h5>
                    <p class="text-muted mb-0">
                        Dashboard loaded successfully.
                    </p>
                </div>
            `;

            sectionCache[section] = html;
            renderMain(html);
        }

        else if (section === "analytics") {
            setHeader("Advanced Analytics");
            await loadAnalytics(forceRefresh);
        }

        else if (section === "users") {
            setHeader("User Management");

            const users = await fetchAdminData("admin/users");
            const html = renderUserTable(users);

            sectionCache[section] = html;
            renderMain(html);
        }

        else if (section === "events") {
            setHeader(
                "Event Management",
                `
                <button class="btn btn-primary btn-sm"
                    onclick="openCreateEventModal()">
                    + Create Event
                </button>
                `
            );

            const events = await fetchAdminData("/events/events");
            const html = renderEventAdminTable(events);

            sectionCache[section] = html;
            renderMain(html);
        }

        else if (section === "bookings") {
            setHeader("All Bookings");

            const bookings = await fetchAdminData("/admin/bookings");
            const html = renderBookingTable(bookings);

            sectionCache[section] = html;
            renderMain(html);
        }

    } catch (err) {
        console.error(err);
        renderMain(`
            <div class="alert alert-danger">
                Failed to load section.
            </div>
        `);
    }

    loadingSection = false;
}

function setTitleBySection(section) {
    if (section === "stats") setHeader("Analytics Dashboard");
    if (section === "analytics") setHeader("Advanced Analytics");
    if (section === "users") setHeader("User Management");
    if (section === "events") {
        setHeader(
            "Event Management",
            `<button class="btn btn-primary btn-sm"
                onclick="openCreateEventModal()">+ Create Event</button>`
        );
    }
    if (section === "bookings") setHeader("All Bookings");
}

/* ===================================================
   TABLES
=================================================== */
function renderUserTable(users) {
    return `
    <div class="card bg-dark border-secondary">
        <table class="table table-dark table-hover mb-0">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${users.map(u => `
                <tr>
                    <td>${u.id}</td>
                    <td>${u.username}</td>
                    <td><span class="badge bg-secondary">${u.role}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-danger"
                            onclick="deleteUser(${u.id})">
                            Delete
                        </button>
                    </td>
                </tr>
                `).join("")}
            </tbody>
        </table>
    </div>`;
}

function renderBookingTable(bookings) {
    return `
    <div class="card bg-dark border-secondary">
        <table class="table table-dark table-hover mb-0">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>User</th>
                    <th>Event</th>
                    <th>Date</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                ${bookings.map(b => `
                <tr>
                    <td>${b.id}</td>
                    <td>${b.user_name || ("User " + b.user_id)}</td>
                    <td>${b.event_title || ("Event " + b.event_id)}</td>
                    <td>${new Date().toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-danger"
                            onclick="deleteBooking(${b.id})">
                            Cancel
                        </button>
                    </td>
                </tr>
                `).join("")}
            </tbody>
        </table>
    </div>`;
}

function renderEventAdminTable(events) {
    const displayEvents = events.slice(0, 10);

    return `
    <div class="card bg-dark border-secondary">
        <table class="table table-dark table-hover mb-0">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Event</th>
                    <th>Location</th>
                    <th>Category</th>
                    <th>Price</th>
                    <th>Seats</th>
                    <th>Date</th>
                    <th>Actions</th>
                </tr>
            </thead>

            <tbody>
                ${displayEvents.map((e, i) => `
                <tr>
                    <td>${i + 1}</td>
                    <td>${e.title}</td>
                    <td>${e.location}</td>
                    <td>${e.category || "General"}</td>
                    <td>₹${e.price}</td>
                    <td>${e.available_seats}/${e.total_seats}</td>
                    <td>${e.date_time}</td>
                    <td>
                        <button onclick="editEvent(${e.id})">Edit</button>
                        <button onclick="deleteEvent(${e.id})">Delete</button>
                    </td>
                </tr>
                `).join("")}
            </tbody>
        </table>
    </div>`;
}

/* ===================================================
   API
=================================================== */
async function fetchAdminData(endpoint) {
    const token = getToken();

    const res = await fetch(`${API_URL}${endpoint}`, {
        headers: {
            Authorization: `Bearer ${token}`
        }
    });

    return await res.json();
}

/* ===================================================
   SEARCH
=================================================== */
function bindSearch() {
    const search = document.getElementById("adminEventSearch");
    if (!search) return;

    search.addEventListener("input", () => {
        const q = search.value.toLowerCase();

        if (!sectionCache[currentSection]) return;

        if (currentSection === "users") {
            fetchAdminData("/admin/admin/users").then(data => {
                const filtered = data.filter(u =>
                    u.username.toLowerCase().includes(q)
                );
                renderMain(renderUserTable(filtered));
            });
        }

        if (currentSection === "events") {
            fetchAdminData(`/events/events?title=${q}`).then(data => {
                renderMain(renderEventAdminTable(data));
            });
        }

        if (currentSection === "bookings") {
            fetchAdminData("admin/bookings").then(data => {
                const filtered = data.filter(b =>
                    (b.user_name || "").toLowerCase().includes(q) ||
                    (b.event_title || "").toLowerCase().includes(q)
                );
                renderMain(renderBookingTable(filtered));
            });
        }
    });
}

/* ===================================================
   ANALYTICS
=================================================== */
let analyticsData = null;

async function loadAnalytics(forceRefresh = false) {
    const main = document.getElementById("admin-main-view");

    if (analyticsData && !forceRefresh) {
        main.innerHTML = analyticsData.html;
        renderAnalyticsCharts();
        return;
    }

    showLoader();

    try {
        const stats = await fetchAdminData("/analytics/stats");
        const revenueTrend = await fetchAdminData("/analytics/admin/analytics/revenue-trend");
        const bookingsTrend = await fetchAdminData("/analytics/admin/analytics/bookings-trend");
        const mostBooked = await fetchAdminData("/analytics/admin/analytics/most-booked");

        const html = `
        <div class="analytics-page">

            <div class="row g-3 mb-3">

                <div class="col-md-3">
                    <div class="card p-3 metric-card">
                        <small>Users</small>
                        <h4>${stats.total_users}</h4>
                    </div>
                </div>

                <div class="col-md-3">
                    <div class="card p-3 metric-card">
                        <small>Events</small>
                        <h4>${stats.total_events}</h4>
                    </div>
                </div>

                <div class="col-md-3">
                    <div class="card p-3 metric-card">
                        <small>Bookings</small>
                        <h4>${stats.total_bookings}</h4>
                    </div>
                </div>

                <div class="col-md-3">
                    <div class="card p-3 metric-card">
                        <small>Revenue</small>
                        <h4>₹${stats.revenue}</h4>
                    </div>
                </div>

            </div>

            <div class="row g-3 mb-3">

                <div class="col-lg-6">
                    <div class="card p-3 chart-card">
                        <h6>Revenue Trend</h6>
                        <canvas id="revenueChart"></canvas>
                    </div>
                </div>

                <div class="col-lg-6">
                    <div class="card p-3 chart-card">
                        <h6>Bookings Trend</h6>
                        <canvas id="bookingChart"></canvas>
                    </div>
                </div>

            </div>

            <div class="row g-3 mb-3">

                <div class="col-lg-6">
                    <div class="card p-3 chart-card">
                        <h6>User Growth</h6>
                        <canvas id="userChart"></canvas>
                    </div>
                </div>

                <div class="col-lg-6">
                    <div class="card p-3 chart-card">
                        <h6>Top Events Share</h6>
                        <canvas id="eventPieChart"></canvas>
                    </div>
                </div>

            </div>

            <div class="card p-3">
                <h6 class="mb-3">Top Events</h6>

                ${mostBooked.map(e => `
                    <div class="d-flex justify-content-between py-2 border-bottom border-secondary">
                        <span>${e.title}</span>
                        <span>${e.bookings}</span>
                    </div>
                `).join("")}
            </div>

        </div>`;

        analyticsData = {
            html,
            revenueTrend,
            bookingsTrend,
            mostBooked
        };

        sectionCache.analytics = html;
        main.innerHTML = html;

        renderAnalyticsCharts();

    } catch (err) {
        console.error(err);
        main.innerHTML = `<div class="text-danger">Failed to load analytics</div>`;
    }
}

function renderAnalyticsCharts() {
    if (!analyticsData) return;

    const rev = document.getElementById("revenueChart");
    const book = document.getElementById("bookingChart");

    if (!rev || !book) return;

    new Chart(rev, {
        type: "line",
        data: {
            labels: analyticsData.revenueTrend.map(i => i.date),
            datasets: [{
                label: "Revenue",
                data: analyticsData.revenueTrend.map(i => i.revenue),
                tension: 0.4
            }]
        }
    });

    new Chart(book, {
        type: "bar",
        data: {
            labels: analyticsData.bookingsTrend.map(i => i.date),
            datasets: [{
                label: "Bookings",
                data: analyticsData.bookingsTrend.map(i => i.bookings)
            }]
        }
    });
}