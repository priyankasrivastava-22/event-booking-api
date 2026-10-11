"use strict";

const API_BASE = "https://event-booking-api-gnww.onrender.com/api";
let currentPage = 1;
let editingUserId = null;

function getToken() { return localStorage.getItem("token") || localStorage.getItem("access_token"); }
function authHeaders() { const t = getToken(); return t ? { "Authorization": `Bearer ${t}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" }; }
function escapeHtml(v) { return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[c])); }
function debounce(fn, delay) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), delay); }; }

document.addEventListener("DOMContentLoaded", () => {
    loadUsers(1);
    document.getElementById("filterSearch").addEventListener("input", debounce(() => loadUsers(1), 400));
    document.getElementById("filterRole").addEventListener("change", () => loadUsers(1));
    document.getElementById("filterStatus").addEventListener("change", () => loadUsers(1));
});

async function loadUsers(page = 1) {
    currentPage = page;
    const search = document.getElementById("filterSearch").value.trim();
    const role = document.getElementById("filterRole").value;
    const status = document.getElementById("filterStatus").value;

    const params = new URLSearchParams({ page, limit: 10 });
    if (search) params.append("search", search);
    if (role) params.append("role", role);
    if (status) params.append("status", status);

    const tbody = document.getElementById("usersTableBody");
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">Loading...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/admin/users/list?${params.toString()}`, { headers: authHeaders() });
        if (res.status === 401) { window.location.href = "../../pages/login.html"; return; }
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();

        if (!data.items || !data.items.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No users found.</td></tr>`;
            renderPagination(0, 1, 10);
            return;
        }

        tbody.innerHTML = data.items.map(u => {
            const displayName = u.full_name || u.username;
            const avatar = u.profile_image
                ? `<img class="user-avatar" src="${u.profile_image}" alt="">`
                : `<div class="user-avatar-fallback">${escapeHtml(displayName[0]?.toUpperCase() || "U")}</div>`;

            return `
                <tr>
                    <td><div class="user-cell">${avatar}<span>${escapeHtml(displayName)}</span></div></td>
                    <td>${escapeHtml(u.email || "—")}</td>
                    <td><span class="role-badge ${u.role}">${escapeHtml(u.role)}</span></td>
                    <td>${u.bookings_count}</td>
                    <td><span class="status-badge ${u.is_active ? "active" : "inactive"}">${u.is_active ? "Active" : "Inactive"}</span></td>
                    <td>
                        <button class="action-icon-btn" title="View" onclick="viewUser(${u.id}, '${escapeHtml(displayName)}', '${escapeHtml(u.email || "")}', '${u.role}', ${u.bookings_count}, ${u.is_active})"><i class="bi bi-eye"></i></button>
                        <button class="action-icon-btn" title="Edit" onclick="openEditUserModal(${u.id}, '${u.role}', ${u.is_active})"><i class="bi bi-pencil"></i></button>
                        <button class="action-icon-btn danger" title="Delete" onclick="deleteUser(${u.id})"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>
            `;
        }).join("");

        renderPagination(data.total, data.page, data.limit);

    } catch (error) {
        console.error("Load users error:", error);
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">Unable to load users.</td></tr>`;
    }
}

function renderPagination(total, page, limit) {
    const totalPages = Math.max(1, Math.ceil(total / limit));
    const container = document.getElementById("paginationControls");
    const summary = document.getElementById("paginationSummary");

    let buttons = `<button ${page <= 1 ? "disabled" : ""} onclick="loadUsers(${page - 1})"><i class="bi bi-chevron-left"></i></button>`;
    let start = Math.max(1, page - 2);
    let end = Math.min(totalPages, start + 4);
    start = Math.max(1, end - 4);
    for (let i = start; i <= end; i++) buttons += `<button class="${i === page ? "active" : ""}" onclick="loadUsers(${i})">${i}</button>`;
    buttons += `<button ${page >= totalPages ? "disabled" : ""} onclick="loadUsers(${page + 1})"><i class="bi bi-chevron-right"></i></button>`;

    container.innerHTML = buttons;
    const from = total === 0 ? 0 : (page - 1) * limit + 1;
    const to = Math.min(page * limit, total);
    summary.textContent = `Showing ${from} to ${to} of ${total} users`;
}

function viewUser(id, name, email, role, bookings, isActive) {
    document.getElementById("viewUserBody").innerHTML = `
        <p><strong>Name:</strong> ${name}</p>
        <p><strong>Email:</strong> ${email || "—"}</p>
        <p><strong>Role:</strong> ${role}</p>
        <p><strong>Bookings:</strong> ${bookings}</p>
        <p><strong>Status:</strong> ${isActive ? "Active" : "Inactive"}</p>
    `;
    bootstrap.Modal.getOrCreateInstance(document.getElementById("viewUserModal")).show();
}

function openEditUserModal(id, role, isActive) {
    editingUserId = id;
    document.getElementById("edit_userRole").value = role;
    document.getElementById("edit_userStatus").value = String(isActive);
    bootstrap.Modal.getOrCreateInstance(document.getElementById("editUserModal")).show();
}

async function saveEditedUser() {
    const payload = {
        role: document.getElementById("edit_userRole").value,
        is_active: document.getElementById("edit_userStatus").value === "true"
    };
    try {
        const res = await fetch(`${API_BASE}/admin/users/${editingUserId}`, { method: "PUT", headers: authHeaders(), body: JSON.stringify(payload) });
        if (!res.ok) throw new Error("Failed to update user");
        bootstrap.Modal.getOrCreateInstance(document.getElementById("editUserModal")).hide();
        loadUsers(currentPage);
    } catch (error) {
        alert("Unable to save changes.");
    }
}

async function deleteUser(id) {
    if (!confirm("Delete this user? This cannot be undone.")) return;
    try {
        const res = await fetch(`${API_BASE}/admin/users/${id}`, { method: "DELETE", headers: authHeaders() });
        if (!res.ok) throw new Error();
        loadUsers(currentPage);
    } catch (error) {
        alert("Unable to delete user.");
    }
}