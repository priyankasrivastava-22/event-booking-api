document.addEventListener("DOMContentLoaded", () => {
    const footerTarget = document.getElementById("footer-placeholder");

    if (footerTarget) {
        fetch("footer.html")
            .then(response => response.text())
            .then(data => {
                footerTarget.innerHTML = data;
            })
            .catch(error => {
                console.error("Footer failed to load:", error);
            });
    }
});