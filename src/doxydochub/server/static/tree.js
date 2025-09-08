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
    content.innerHTML = `
        <h2><i class="fa-solid fa-diagram-project"></i> ${project.name}</h2>

        <div class="card">
            <h3><i class="fa-solid fa-info-circle"></i> Generic Info</h3>
            <p><strong>Origin:</strong> <a href="${project.origin_url}" target="_blank">${project.origin_url}</a></p>
            <p><strong>Created at:</strong> ${new Date(project.created_at).toLocaleString()}</p>
        </div>

        <div class="card">
            <h3><i class="fa-solid fa-key"></i> Metadata</h3>
            <ul class="metadata-list">
                ${Object.entries(project.metadata).map(([k,v]) => `<li><strong>${k}:</strong> ${v}</li>`).join("")}
            </ul>
        </div>

        <div class="card">
            <h3><i class="fa-solid fa-code-branch"></i> Versions</h3>
            <ul class="versions-list">
                ${project.versions.map(v => `
                    <li class="${project.latest_version_id === v.id ? 'latest-version' : ''}">
                        <i class="fa-solid fa-circle${project.latest_version_id === v.id ? '' : '-dot'}"></i>
                        ${v.version} <span class="version-date">(${new Date(v.created_at).toLocaleString()})</span>
                    </li>
                `).join("")}
            </ul>
        </div>
    `;
}
