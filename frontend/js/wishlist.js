document.addEventListener("DOMContentLoaded", () => {

    loadWishlist();

    document.getElementById("backBtn")
        .addEventListener("click", () => {
            window.location.href = "events.html";
        });

    document.getElementById("wishlistSearchInput")
        .addEventListener("input", loadWishlist);
});

function loadWishlist() {

    const container =
        document.getElementById("wishlistContainer");

    const search =
        document.getElementById("wishlistSearchInput")
        ?.value
        ?.toLowerCase() || "";

    const wishlist =
        JSON.parse(localStorage.getItem("wishlist")) || [];

    const filtered =
        wishlist.filter(event =>
            event.title.toLowerCase().includes(search)
        );

    container.innerHTML = "";

    if(filtered.length === 0){

        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <h4>No saved events</h4>
            </div>
        `;
        return;
    }

    filtered.forEach(event => {

        container.innerHTML += `
        <div class="col mb-3">

            <div class="wishlist-card">

                <img
                    src="${event.image_url}"
                    class="wishlist-image">

                <div class="wishlist-content">

                    <div class="d-flex justify-content-between">

                        <h5>${event.title}</h5>

                        <button
                            class="remove-btn"
                            onclick="removeWishlist(${event.id})">

                            <i class="bi bi-heart-fill"></i>

                        </button>

                    </div>

                    <p>
                        <i class="bi bi-geo-alt"></i>
                        ${event.location}
                    </p>

                    <p>
                        ${event.category}
                    </p>

                    <h6>₹${event.price}</h6>

                    <div class="action-buttons">

                        <button
                            class="btn btn-outline-light"
                            onclick="viewEvent(${event.id})">

                            Details

                        </button>

                        <button
                            class="btn btn-primary">

                            Book Now

                        </button>

                    </div>

                </div>

            </div>

        </div>`;
    });
}

function removeWishlist(id){

    let wishlist =
        JSON.parse(localStorage.getItem("wishlist")) || [];

    wishlist =
        wishlist.filter(event => event.id !== id);

    localStorage.setItem(
        "wishlist",
        JSON.stringify(wishlist)
    );

    loadWishlist();
}

function viewEvent(id){
    window.location.href =
        `event-details.html?id=${id}`;
}