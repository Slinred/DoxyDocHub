document.addEventListener("DOMContentLoaded", () => {
    const toggles = document.querySelectorAll(".tree-item.has-children > .tree-label .toggle");

    toggles.forEach(toggle => {
        toggle.addEventListener("click", (event) => {
            event.stopPropagation();
            const parent = toggle.closest(".tree-item");
            const nested = parent.querySelector(".nested");
            nested.classList.toggle("active");

            // Switch caret icon
            if (nested.classList.contains("active")) {
                toggle.classList.replace("fa-caret-right", "fa-caret-down");
            } else {
                toggle.classList.replace("fa-caret-down", "fa-caret-right");
            }
        });
    });
});
