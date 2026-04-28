// Function to switch between Login, Register, and Forgot views
// This stays global so the HTML 'onclick' can find it.
function showView(viewId) {
    const views = document.querySelectorAll(".auth-view");

    views.forEach(v => {
        v.classList.add("d-none"); // Hide all views
    });

    const activeView = document.getElementById(viewId);
    if (activeView) {
        activeView.classList.remove("d-none"); // Show the one you clicked
    }
}

// Existing Login Logic
const form = document.getElementById("loginForm");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const identifier = form.querySelector("input[type='email']").value;
  const passwordVal = form.querySelector("input[type='password']").value;

  try {
    const res = await fetch("https://event-booking-api-gnww.onrender.com/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: identifier,
        password: passwordVal
      }),
    });

    const data = await res.json();

    if (res.ok) {
      localStorage.setItem("token", data.access_token);
      alert("Login success!");
      window.location.href = "events.html";
    } else {
      alert(data.error || data.detail || "Login failed");
    }
  } catch (err) {
    alert("Server error");
  }
});