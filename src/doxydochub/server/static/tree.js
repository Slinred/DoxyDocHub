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

    // Handle project click on list items
    document.querySelectorAll(".tree-label").forEach(label => {
        label.addEventListener("click", async (event) => {
            // Stop event from bubbling to parent labels
            event.stopPropagation();

            const item = label.closest(".tree-item");
            const projectId = item.getAttribute("data-id");
            if (!projectId) return;

            const response = await fetch(`/api/projects/${projectId}`);
            if (!response.ok) {
                console.error("Failed to fetch project", response.statusText);
                return;
            }

            const project = await response.json();
            renderProjectDetails(project);
        });
    });

});

function renderProjectDetails(project) {
    const content = document.getElementById("project-content");
    content.innerHTML = "";

    const title = document.createElement("h2");
    title.textContent = `Project: ${project.name}`;
    content.appendChild(title);

    const grid = document.createElement("div");
    grid.className = "grid";

    // --- Generic Info Card ---
    const genericCard = document.createElement("div");
    genericCard.className = "card";
    genericCard.innerHTML = `
        <h3>Generic Info</h3>
        <p><strong>Origin URL:</strong> ${project.origin_url}</p>
        <p><strong>Created At:</strong> ${project.created_at}</p>
    `;
    grid.appendChild(genericCard);

    // --- Metadata Card ---
    const metadataCard = document.createElement("div");
    metadataCard.className = "card";
    metadataCard.innerHTML = `<h3>Metadata</h3>`;
    const metadataList = document.createElement("ul");
    for (const [key, value] of Object.entries(project.metadata)) {
        const li = document.createElement("li");
        li.textContent = `${key}: ${value}`;
        metadataList.appendChild(li);
    }
    metadataCard.appendChild(metadataList);
    grid.appendChild(metadataCard);

    // --- Versions Card ---
    const versionsCard = document.createElement("div");
    versionsCard.className = "card";
    versionsCard.innerHTML = `<h3>Versions</h3>`;
    const versionList = document.createElement("ul");

    project.versions.forEach(version => {
        const li = document.createElement("li");
        li.textContent = version.version;

        if (version.has_docs) {
            const link = document.createElement("a");
            link.href = `/docs/${project.id}/${version.id}/index.html`;
            link.target = "_blank";
            link.textContent = " (Open Docs)";
            li.appendChild(link);
        }
        versionList.appendChild(li);
    });

    versionsCard.appendChild(versionList);
    grid.appendChild(versionsCard);

    content.appendChild(grid);
}
