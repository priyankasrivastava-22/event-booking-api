const form = document.getElementById("loginForm");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const email = form.querySelector("input[type='email']").value;
  const password = form.querySelector("input[type='password']").value;

  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  try {
    const res = await fetch("http://127.0.0.1:8000/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
       username: email,
       password: password
     }),
    });

    const data = await res.json();

    if (res.ok) {
      console.log("LOGIN SUCCESS", data);

      // Save token
      localStorage.setItem("token", data.access_token);

      alert("Login successful");

      // Redirect
      window.location.href = "events.html";

    } else {
      alert(data.detail || "Invalid credentials");
    }

  } catch (err) {
    console.error(err);
    alert("Server error");
  }
});