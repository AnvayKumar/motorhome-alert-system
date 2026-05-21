let listings = [];
let currentFilter = "all";
let currentSort = null;

async function loadData() {
    const res = await fetch("listings.json");
    listings = await res.json();

    render();
}

function render() {
    let filtered = [...listings];

    // filter
    if (currentFilter === "Dealer" || currentFilter === "Private Seller") {
        filtered = filtered.filter(x => x.seller_type === currentFilter);
    }

    if (currentFilter === "new") {
        filtered = filtered.filter(x => x.is_new);
    }

    // sort
    if (currentSort === "asc") {
        filtered.sort((a, b) => a.price_numeric - b.price_numeric);
    }

    if (currentSort === "desc") {
        filtered.sort((a, b) => b.price_numeric - a.price_numeric);
    }

    document.getElementById("stats").innerHTML = `
        <div>${filtered.length} listings</div>
        <div>${listings.filter(x => x.is_new).length} new</div>
    `;

    const grid = document.getElementById("grid");
    grid.innerHTML = filtered.map(card).join("");
}

function card(item) {
    return `
    <div class="card">
        <img src="${item.image}" />

        <div class="content">
            <div class="row">
                <span class="badge">${item.is_new ? "NEW" : ""}</span>
                <span class="type">${item.seller_type}</span>
            </div>

            <h3>${item.title}</h3>

            <div class="price">${item.price}</div>

            <div class="summary">${item.summary}</div>

            <a href="${item.url}" target="_blank">View</a>
        </div>
    </div>
    `;
}

// events
document.querySelectorAll(".tabs button").forEach(btn => {
    btn.onclick = () => {
        currentFilter = btn.dataset.filter;
        document.querySelectorAll(".tabs button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        render();
    };
});

document.querySelectorAll(".sort button").forEach(btn => {
    btn.onclick = () => {
        currentSort = btn.dataset.sort;
        render();
    };
});

document.getElementById("search").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();

    document.querySelectorAll(".card").forEach((c, i) => {
        const item = listings[i];
        c.style.display =
            item.title.toLowerCase().includes(q) ||
            item.summary.toLowerCase().includes(q)
                ? "block"
                : "none";
    });
});

loadData();
