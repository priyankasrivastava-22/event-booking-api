"use strict";

const API_BASE = "https://event-booking-api-gnww.onrender.com/api";   // apna backend URL confirm kar lena
let editingCategoryId = null;

function getToken() {
    return localStorage.getItem("token") || localStorage.getItem("access_token");
}

function authHeaders() {
    const token = getToken();
    return token ? { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[c]));
}

// Same keyword-matching approach used for event-details.js's getCategoryIcon(), plus a matching color per category
function getCategoryVisual(name) {
    const value = String(name || "").toLowerCase();
    if (value.includes("tech")) return { icon: "bi-cpu", color: "#3b82f6" };
    if (value.includes("music") || value.includes("concert")) return { icon: "bi-music-note-beamed", color: "#8b5cf6" };
    if (value.includes("business")) return { icon: "bi-briefcase-fill", color: "#f97316" };
    if (value.includes("sport")) return { icon: "bi-trophy-fill", color: "#eab308" };
    if (value.includes("art")) return { icon: "bi-palette-fill", color: "#ec4899" };
    if (value.includes("education")) return { icon: "bi-mortarboard-fill", color: "#06b6d4" };
    if (value.includes("health")) return { icon: "bi-heart-pulse-fill", color: "#ef4444" };
    if (value.includes("comedy")) return { icon: "bi-emoji-laughing-fill", color: "#f59e0b" };
    if (value.includes("festival")) return { icon: "bi-stars", color: "#a855f7" };
    return { icon: "bi-grid-fill", color: "#14b8a6" };                                          // fallback for "Other"/unmatched
}

document.addEventListener("DOMContentLoaded", loadCategories);

// ---------------- LOAD CATEGORIES ----------------
async function loadCategories() {
    const grid = document.getElementById("categoriesGrid");
    grid.innerHTML = `<div class="text-muted text-center py-4">Loading...</div>`;
    try {
        const res = await fetch(`${API_BASE}/engagement/admin/categories-with-counts`, { headers: authHeaders() });
        if (res.status === 401) { window.location.href = "../../pages/login.html"; return; }
        const data = await res.json().catch(() => null);
        if (!res.ok) {
            const message = (data && data.detail) ? data.detail : `Request failed (${res.status})`;
            grid.innerHTML = `<div class="text-danger text-center py-4">${escapeHtml(message)}</div>`;
            console.error("Load categories error:", res.status, data);
            return;
        }
        const categories = Array.isArray(data) ? data : [];
        if (!categories.length) {
            grid.innerHTML = `<div class="text-muted text-center py-4">No categories yet. Add your first one.</div>`;
            return;
        }
        grid.innerHTML = categories.map(cat => {
            const visual = getCategoryVisual(cat.name);
            return `
                <div class="category-card">
                    <div class="category-card-top">
                        <div class="category-icon-chip" style="background:${visual.color}22; color:${visual.color};">
                            <i class="bi ${visual.icon}"></i>
                        </div>
                        <div>
                            <h5>${escapeHtml(cat.name)}</h5>
                            <small>${cat.event_count} Event${cat.event_count === 1 ? "" : "s"}</small>
                        </div>
                    </div>
                    <div class="category-card-actions">
                        <button class="btn-edit" onclick="openEditCategoryModal(${cat.id}, '${escapeHtml(cat.name)}')"><i class="bi bi-pencil"></i> Edit</button>
                        <button class="btn-delete" onclick="deleteCategory(${cat.id}, ${cat.event_count})"><i class="bi bi-trash"></i></button>
                    </div>
                </div>
            `;
        }).join("");
    } catch (error) {
        console.error("Load categories error:", error);
        grid.innerHTML = `<div class="text-danger text-center py-4">Unable to load categories.</div>`;
    }
}

// ---------------- CREATE ----------------
async function createCategory() {
    const name = document.getElementById("newCategoryName").value.trim();
    if (!name) { alert("Category name is required."); return; }
    try {
        const res = await fetch(`${API_BASE}/engagement/admin/categories`, { method: "POST", headers: authHeaders(), body: JSON.stringify({ name }) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to create category.");
        bootstrap.Modal.getOrCreateInstance(document.getElementById("addCategoryModal")).hide();
        document.getElementById("newCategoryName").value = "";
        loadCategories();
    } catch (error) {
        alert(error.message);
    }
}

// ---------------- EDIT ----------------
function openEditCategoryModal(id, name) {
    editingCategoryId = id;
    document.getElementById("editCategoryName").value = name;
    bootstrap.Modal.getOrCreateInstance(document.getElementById("editCategoryModal")).show();
}

async function saveEditedCategory() {
    const name = document.getElementById("editCategoryName").value.trim();
    if (!name) { alert("Category name is required."); return; }
    try {
        const res = await fetch(`${API_BASE}/engagement/admin/categories/${editingCategoryId}`, { method: "PUT", headers: authHeaders(), body: JSON.stringify({ name }) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to update category.");
        bootstrap.Modal.getOrCreateInstance(document.getElementById("editCategoryModal")).hide();
        editingCategoryId = null;
        loadCategories();
    } catch (error) {
        alert(error.message);
    }
}

// ---------------- DELETE ----------------
async function deleteCategory(id, eventCount) {
    const warning = eventCount > 0
        ? `This category has ${eventCount} event(s). Deleting it may affect those events. Continue?`
        : "Delete this category?";
    if (!confirm(warning)) return;
    try {
        const res = await fetch(`${API_BASE}/engagement/admin/categories/${id}`, { method: "DELETE", headers: authHeaders() });
        if (!res.ok) { const data = await res.json().catch(() => ({})); throw new Error(data.detail || "Failed to delete category."); }
        loadCategories();
    } catch (error) {
        alert(error.message);
    }
}