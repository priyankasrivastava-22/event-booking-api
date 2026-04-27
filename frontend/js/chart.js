function renderCharts(trend, mostBooked) {

    // Revenue / Booking Trend Line
    const ctx1 = document.getElementById("revenueChart");

    new Chart(ctx1, {
        type: "line",
        data: {
            labels: trend.map(t => t.date),
            datasets: [{
                label: "Bookings",
                data: trend.map(t => t.bookings),
                borderColor: "#6366f1",
                tension: 0.4
            }]
        }
    });

    // Donut Chart
    const ctx2 = document.getElementById("bookingChart");

    new Chart(ctx2, {
        type: "doughnut",
        data: {
            labels: mostBooked.map(e => e.title),
            datasets: [{
                data: mostBooked.map(e => e.bookings)
            }]
        }
    });
}