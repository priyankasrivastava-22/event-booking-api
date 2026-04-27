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

const API_URL = "http://127.0.0.1:8000";
let currentSection = "stats";

// ---------------- AUTH ----------------
function getToken() {
    const token = localStorage.getItem("token");
    if (!token) {
        alert("Login required");
        window.location.href = "login.html";
        return null;
    }
    return token;
}

// Decode JWT payload (frontend only usage)
function getUserFromToken() {
    const token = localStorage.getItem("token");
    if (!token) return null;

    try {
        return JSON.parse(atob(token.split(".")[1]));
    } catch {
        return null;
    }
}

// Restrict admin access
function protectAdminPage() {
    const user = getUserFromToken();

    if (!user || user.role !== "admin") {
        alert("Access denied. Admins only.");
        window.location.href = "events.html";
    }
}

// ---------------- DASHBOARD NAVIGATION ----------------
document.addEventListener("DOMContentLoaded", () => {
    protectAdminPage();

    document.querySelectorAll('.admin-nav').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();

            document.querySelectorAll('.admin-nav')
                .forEach(l => l.classList.remove('active'));

            link.classList.add('active');

            const section = link.getAttribute('data-section');
            showSection(section);
        });
    });

    showSection('stats');
});

// ---------------- MAIN SECTION HANDLER ----------------
async function showSection(section) {
    currentSection = section;
    const mainView = document.getElementById('admin-main-view');
    const title = document.getElementById('section-title');
    const actions = document.getElementById('header-actions');

    mainView.innerHTML = `
        <div class="text-center mt-5">
            <div class="spinner-border text-primary"></div>
        </div>
    `;
    actions.innerHTML = "";

    if (section === 'stats') {
    title.innerText = "Analytics Dashboard";

    const stats = await fetchAdminData("/stats");


    mainView.innerHTML = `
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

        <div class="mt-4 p-4 card">
            <h5>Recent Activity</h5>
            <p class="text-muted">
                System analytics loaded successfully from backend.
            </p>
        </div>
    `;
}
    else if (section === "analytics") {
    title.innerText = "Analytics Dashboard";
    await loadAnalytics();
    return;
}

    else if (section === 'users') {
        title.innerText = "User Management";

        const users = await fetchAdminData("/admin/users");

        mainView.innerHTML = Array.isArray(users)
            ? renderUserTable(users)
            : `<div class="text-danger p-3">Failed to load users</div>`;
    }

    else if (section === 'events') {
        title.innerText = "Event Management";

        actions.innerHTML = `
            <button class="btn btn-primary btn-sm" onclick="openCreateEventModal()">
                + Create Event
            </button>
        `;

        const events = await fetchAdminData("/events");

        mainView.innerHTML = Array.isArray(events)
            ? renderEventAdminTable(events)
            : `<div class="text-danger p-3">Failed to load events</div>`;
    }

    else if (section === 'bookings') {
        title.innerText = "All Bookings";

        const bookings = await fetchAdminData("/admin/bookings");

        mainView.innerHTML = Array.isArray(bookings)
            ? renderBookingTable(bookings)
            : `<div class="text-danger p-3">Failed to load bookings</div>`;
    }
}

// ---------------- USER TABLE ----------------
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
                `).join('')}
            </tbody>
        </table>
    </div>`;
}

// ---------------- BOOKING TABLE ----------------
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
                    <td>${b.user_name || 'User ' + b.user_id}</td>
                    <td>${b.event_title || 'Event ' + b.event_id}</td>
                    <td>${new Date().toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-danger"
                            onclick="deleteBooking(${b.id})">
                            Cancel
                        </button>
                    </td>
                </tr>
                `).join('')}
            </tbody>
        </table>
    </div>`;
}

// ---------------- EVENT TABLE ----------------
function renderEventAdminTable(events) {
    const displayEvents = events.slice(0, 10);

    return `
    <table class="table table-dark table-hover align-middle mb-0">
        <thead class="table-light text-dark">
            <tr>
                <th>#</th>
                <th>Event Name</th>
                <th>Location</th>
                <th>Category</th>
                <th>Price</th>
                <th>Seats</th>
                <th>Date</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            ${displayEvents.map((e, index) => `
            <tr>
                <td>${index + 1}</td>
                <td>${e.title}</td>
                <td>${e.location}</td>
                <td>${e.category || 'General'}</td>
                <td>₹${e.price}</td>
                <td>${e.available_seats}/${e.total_seats}</td>
                <td>${e.date_time}</td>
                <td>
                    <button onclick="editEvent(${e.id})">Edit</button>
                    <button onclick="deleteEvent(${e.id})">Delete</button>
                </td>
            </tr>
            `).join('')}
        </tbody>
    </table>`;
}

// ---------------- ANALYTICS UI ----------------
function renderAnalyticsUI(data, revenueData, trendData) {
    return `
    <div class="row g-4">

        <!-- CARDS -->
        <div class="col-md-3">
            <div class="card analytics-card">
                <p>Total Revenue</p>
                <h3>₹${revenueData.total_revenue}</h3>
            </div>
        </div>

        <div class="col-md-3">
            <div class="card analytics-card">
                <p>Total Bookings</p>
                <h3>${data.total_bookings}</h3>
            </div>
        </div>

        <div class="col-md-3">
            <div class="card analytics-card">
                <p>Total Users</p>
                <h3>${data.total_users}</h3>
            </div>
        </div>

        <div class="col-md-3">
            <div class="card analytics-card">
                <p>Total Events</p>
                <h3>${data.total_events}</h3>
            </div>
        </div>

        <!-- CHARTS -->
        <div class="col-md-8">
            <div class="card p-3">
                <h6>Revenue Overview</h6>
                <canvas id="revenueChart"></canvas>
            </div>
        </div>

        <div class="col-md-4">
            <div class="card p-3">
                <h6>Bookings Distribution</h6>
                <canvas id="bookingChart"></canvas>
            </div>
        </div>

    </div>
    `;
}


// ---------------- API HELPER ----------------
async function fetchAdminData(endpoint) {
    const token = getToken();

    const res = await fetch(`${API_URL}${endpoint}`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    return await res.json();
}

// =====================================================
// ADDED FUNCTIONS (THIS FIXES YOUR PROBLEM)
// =====================================================

// ---------------- DELETE USER ----------------
async function deleteUser(id) {
    const token = getToken();

    const res = await fetch(`${API_URL}/admin/users/${id}`, {
        method: "DELETE",
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    if (res.ok) {
        alert("User deleted");
        showSection("users");
    } else {
        alert("Failed to delete user");
    }
}

// ---------------- DELETE EVENT ----------------
async function deleteEvent(id) {
    const token = getToken();

    const res = await fetch(`${API_URL}/admin/events/${id}`, {
        method: "DELETE",
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    if (res.ok) {
        alert("Event deleted");
        showSection("events");
    } else {
        alert("Failed to delete event");
    }
}

// ---------------- EDIT EVENT (basic placeholder) ----------------
let currentEditEventId = null;

// Open modal and prefill data
async function editEvent(id) {
    const token = getToken();

    const res = await fetch(`${API_URL}/events`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const events = await res.json();
    const event = events.find(e => e.id === id);

    if (!event) {
        alert("Event not found");
        return;
    }

    currentEditEventId = id;

    document.getElementById("edit_title").value = event.title || "";
    document.getElementById("edit_location").value = event.location || "";
    document.getElementById("edit_price").value = event.price || 0;
    document.getElementById("edit_seats").value = event.total_seats || 0;
    document.getElementById("edit_date").value = event.date_time || "";
    document.getElementById("edit_description").value = event.description || "";

    const modal = new bootstrap.Modal(document.getElementById("editEventModal"));
    modal.show();
}

// Save edited event
async function saveEditedEvent() {
    const token = getToken();

    const body = {
        title: document.getElementById("edit_title").value,
        location: document.getElementById("edit_location").value,
        price: parseInt(document.getElementById("edit_price").value),
        total_seats: parseInt(document.getElementById("edit_seats").value),
        date_time: document.getElementById("edit_date").value,
        description: document.getElementById("edit_description").value
    };

    const res = await fetch(`${API_URL}/events/${currentEditEventId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(body)
    });

    if (res.ok) {
        alert("Event updated successfully");
        bootstrap.Modal.getInstance(document.getElementById("editEventModal")).hide();
        showSection("events");
    } else {
        alert("Update failed");
    }
}

// -------------------- DELETE BOOKING ---------------------
// ---------------- CANCEL BOOKING (ADMIN) ----------------
async function deleteBooking(id) {
    const token = getToken();

    if (!confirm("Cancel this booking?")) return;

    const res = await fetch(`${API_URL}/admin/bookings/${id}`, {
        method: "DELETE",
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    if (res.ok) {
        alert("Booking cancelled successfully");

        // refresh bookings table
        showSection("bookings");
    } else {
        const err = await res.text();
        console.error(err);
        alert("Failed to cancel booking");
    }
}

// ---------------- CREATE EVENT MODAL OPEN ----------------
function openCreateEventModal() {
    const modal = document.getElementById("createEventModal");

    if (!modal) {
        alert("Create Event modal not found in HTML");
        return;
    }

    modal.style.display = "block";
}


// ---------------- EVENT SEARCH ----------------
document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("adminEventSearch");

    if (!searchInput) return;

    searchInput.addEventListener("input", async (e) => {
        const query = e.target.value;
        const token = getToken();

        // ---------------- EVENTS SEARCH ----------------
        if (currentSection === "events") {

            const res = await fetch(`${API_URL}/events?title=${query}`, {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            const data = await res.json();
            document.getElementById("admin-main-view").innerHTML =
                renderEventAdminTable(data);
        }

        // ---------------- USERS SEARCH ----------------
        else if (currentSection === "users") {

            const res = await fetch(`${API_URL}/admin/users`, {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            let data = await res.json();

            data = data.filter(u =>
                u.username.toLowerCase().includes(query.toLowerCase())
            );

            document.getElementById("admin-main-view").innerHTML =
                renderUserTable(data);
        }

        // ---------------- BOOKINGS SEARCH ----------------
        else if (currentSection === "bookings") {

            const res = await fetch(`${API_URL}/admin/bookings`, {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            let data = await res.json();

            data = data.filter(b =>
                (b.user_name || "").toLowerCase().includes(query.toLowerCase()) ||
                (b.event_title || "").toLowerCase().includes(query.toLowerCase())
            );

            document.getElementById("admin-main-view").innerHTML =
                renderBookingTable(data);
        }
    });
});

async function loadAnalytics() {
    const mainView = document.getElementById("admin-main-view");

    mainView.innerHTML = `
        <div class="text-center mt-5">
            <div class="spinner-border text-primary"></div>
        </div>
    `;

    try {
        const stats = await fetchAdminData("/stats");
        const revenueTrend = await fetchAdminData("/admin/analytics/revenue-trend");
        const bookingsTrend = await fetchAdminData("/admin/analytics/bookings-trend");
        const mostBooked = await fetchAdminData("admin/analytics/most-booked");

        mainView.innerHTML = `
            <div class="row g-4">

                <!-- TOP CARDS -->
                <div class="col-md-3">
                    <div class="card p-3 bg-primary text-white">
                        <h6>Users</h6>
                        <h3>${stats.total_users}</h3>
                    </div>
                </div>

                <div class="col-md-3">
                    <div class="card p-3 bg-success text-white">
                        <h6>Events</h6>
                        <h3>${stats.total_events}</h3>
                    </div>
                </div>

                <div class="col-md-3">
                    <div class="card p-3 bg-info text-white">
                        <h6>Bookings</h6>
                        <h3>${stats.total_bookings}</h3>
                    </div>
                </div>

                <div class="col-md-3">
                    <div class="card p-3 bg-warning text-white">
                        <h6>Revenue</h6>
                        <h3>₹${stats.revenue}</h3>
                    </div>
                </div>

                <!-- REVENUE CHART -->
                <div class="col-md-8">
                    <div class="card p-3">
                        <h6>Revenue Trend (Last 7 Days)</h6>
                        <canvas id="revenueChart"></canvas>
                    </div>
                </div>

                <!-- BOOKINGS CHART -->
                <div class="col-md-4">
                    <div class="card p-3">
                        <h6>Bookings Trend</h6>
                        <canvas id="bookingChart"></canvas>
                    </div>
                </div>

                <!-- TOP EVENTS -->
                <div class="col-12 card p-3">
                    <h5>Top Events</h5>
                    ${
                        mostBooked.map(e => `
                            <div class="d-flex justify-content-between border-bottom py-2">
                                <span>${e.title}</span>
                                <span>${e.bookings} bookings</span>
                            </div>
                        `).join("")
                    }
                </div>

            </div>
        `;

        // ---------------- CHART 1: REVENUE ----------------
        const revenueLabels = revenueTrend.map(r => r.date);
        const revenueData = revenueTrend.map(r => r.revenue);

        new Chart(document.getElementById("revenueChart"), {
            type: "line",
            data: {
                labels: revenueLabels,
                datasets: [{
                    label: "Revenue",
                    data: revenueData,
                    fill: true,
                    tension: 0.4
                }]
            }
        });

        // ---------------- CHART 2: BOOKINGS ----------------
        const bookingLabels = bookingsTrend.map(b => b.date);
        const bookingData = bookingsTrend.map(b => b.bookings);

        new Chart(document.getElementById("bookingChart"), {
            type: "bar",
            data: {
                labels: bookingLabels,
                datasets: [{
                    label: "Bookings",
                    data: bookingData
                }]
            }
        });

    } catch (err) {
        console.error(err);
        mainView.innerHTML = `<div class="text-danger p-3">Failed to load analytics</div>`;
    }
}