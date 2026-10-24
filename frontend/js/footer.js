"use strict";
// A single reusable fragment for customer pages, independent of current route.
document.addEventListener("DOMContentLoaded", async () => {
    const target = document.getElementById("footer-placeholder");
    if (!target) return;
    try {
        const response = await fetch("../components/footer.html");
        if (!response.ok) throw new Error(`Footer HTTP ${response.status}`);
        target.innerHTML = await response.text();
    } catch (error) {
        console.error("Footer failed to load", error);
        target.textContent = "Eventora · Browse and manage your bookings.";
    }
});
