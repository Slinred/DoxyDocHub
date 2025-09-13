document.addEventListener("DOMContentLoaded", () => {

  const titleLink = document.getElementById("header-title-link");
    if (titleLink) {
        titleLink.addEventListener("click", function(e) {
            e.preventDefault();
            localStorage.clear();
            window.location.href = "/";
        });
    }

    const expanded = getExpandedItems();
    expanded.forEach(id => {
        const item = document.querySelector(`.tree-item[data-id='${id}'] .nested`);
        if (item) {
          item.classList.add("active");
          const bookIcon = item.parentElement.querySelector(".tree-book-icon");
          if (bookIcon) bookIcon.click()
        }
    });

    const bookIcons = document.querySelectorAll(".tree-item.has-children > .tree-label .tree-book-icon");
    bookIcons.forEach(bookIcon => {
        bookIcon.addEventListener("click", (event) => {
            event.stopPropagation();
            const parent = bookIcon.closest(".tree-item");
            const id = parent.getAttribute("data-id");
            let expanded = getExpandedItems();

            const nested = parent.querySelector(".nested");
            nested.classList.toggle("active");

            // Switch book icon
            if (nested.classList.contains("active")) {
                if (!expanded.includes(id)) expanded.push(id);
                bookIcon.innerHTML = `<span class="iconify" data-icon="mdi:book-minus-multiple"></span>`;
            } else {
                expanded = expanded.filter(x => x !== id);
                bookIcon.innerHTML = `<span class="iconify" data-icon="mdi:book-plus-multiple"></span>`;
            }
            setExpandedItems(expanded);
        });
    });

    // Handle project click on list items
    document.querySelectorAll(".tree-label").forEach(label => {
        label.addEventListener("click", async (event) => {
            // Stop event from bubbling to parent labels
            event.stopPropagation();
            fetchAndRenderProjectDetails(label);
        });
    });

    const selectedId = getSelectedProject();
    if (selectedId) {
        const label = document.querySelector(`.tree-item[data-id='${selectedId}'] .tree-label`);
        if (label) fetchAndRenderProjectDetails(label);
    }
});

async function fetchAndRenderProjectDetails(label) {
  const item = label.closest(".tree-item");
  const projectId = item.getAttribute("data-id");
  if (!projectId) return;

  setSelectedProject(projectId);

  const response = await fetch(`/api/projects/${projectId}`);
  if (!response.ok) {
      console.error("Failed to fetch project", response.statusText);
      return;
  }

  const project = await response.json();
  renderProjectDetails(project);
}

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
        li.className = "version-item";
        const nameSpan = document.createElement("span");
        nameSpan.innerHTML = version.version + " <span class='iconify' data-icon='mdi:arrow-right-thin'></span>";
        nameSpan.classList.add("version-name");
        // nameSpan.style.cursor = "pointer";
        li.appendChild(nameSpan);

        if (version.has_docs) {
            const iframeSpan = document.createElement("span");
            iframeSpan.className ="version-doc-link";
            iframeSpan.title = "View in embedded frame";
            iframeSpan.style.cursor = "pointer";
            iframeSpan.addEventListener("click", () => {
                showVersionInContent(project, version);
            });
            iframeSpan.innerHTML = `<span class="iconify" data-icon="mdi:book-open-page-variant"></span>`;
            li.appendChild(iframeSpan);

            const link = document.createElement("a");
            link.className = "version-doc-link";
            link.href = `/docs/${project.name_slug}/${version.version_slug}/index.html`;
            link.target = "_blank";
            link.innerHTML = ` <span class="iconify" data-icon="mdi:open-in-new"></span>`;
            li.appendChild(link);
        }
        else {
            const noDocsSpan = document.createElement("span");
            noDocsSpan.style.color = "#888";
            noDocsSpan.style.marginLeft = "8px";
            noDocsSpan.textContent = "(no docs)";
            li.appendChild(noDocsSpan);
        }

        versionList.appendChild(li);
    });


    versionsCard.appendChild(versionList);
    grid.appendChild(versionsCard);

    content.appendChild(grid);
}

function showVersionInContent(project, version) {
    const content = document.getElementById("project-content");
    content.innerHTML = `
        <div class="version-header">
            <button class="back-btn">⬅ Back</button>
            <h2>${project.name} – ${version.version}</h2>
        </div>
        <div id="iframe-loader" class="loader">
            <svg class="spinner" viewBox="0 0 50 50">
                <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
            </svg>
            <p>Loading documentation...</p>
        </div>
        <iframe id="docs-frame" src="/docs/${project.name_slug}/${version.version_slug}/index.html" class="hidden"></iframe>
    `;

    // Back button → re-render project details
    content.querySelector(".back-btn").addEventListener("click", () => {
        renderProjectDetails(project);
    });

    const iframe = document.getElementById("docs-frame");
    const loader = document.getElementById("iframe-loader");
    iframe.onload = () => {
        loader.style.display = "none";
        iframe.classList.remove("hidden");
    };

  // Setup handlers to force navigation INSIDE the iframe.
  // This will run after each load so it applies for dynamically loaded pages too.
  iframe.addEventListener("load", () => {
    try {
      const doc = iframe.contentDocument;
      const win = iframe.contentWindow;

      // Remove any <base target="..."> that might force top navigation
      try {
        const base = doc.querySelector("base[target]");
        if (base) base.removeAttribute("target");
      } catch (e) { /* ignore */ }

      // Force all anchors to open in same frame and intercept clicks.
      try {
        doc.querySelectorAll("a").forEach(a => a.target = "_self");
      } catch (e) { /* ignore */ }

      // Override window.open inside iframe so JS opening windows stays inside iframe
      try {
        win.open = function(url, target, features) {
          // compute absolute url relative to current iframe location
          const newUrl = new URL(url, win.location.href).toString();
          win.location.href = newUrl;
          return null;
        };
      } catch (e) { /* ignore */ }

      // Intercept click events on anchors (capturing) and force the iframe to navigate,
      // this covers anchors added dynamically or anchors with onclick handlers.
      try {
        // Remove previous listener if any (idempotent)
        if (win.__doxydochub_nav_listener_installed) {
          // nothing — we keep single installation guard
        } else {
          doc.addEventListener("click", function(e) {
            const a = e.target.closest && e.target.closest("a");
            if (!a) return;

            // ignore if anchor is just an in-page anchor (#) or javascript:
            const href = a.getAttribute("href");
            if (!href || href.startsWith("javascript:") || href === "#") return;

            // Prevent top-level navigation / new tab
            e.preventDefault();
            e.stopPropagation();

            // resolve full URL relative to iframe document and navigate inside iframe
            const newUrl = new URL(href, doc.location.href).toString();
            win.location.href = newUrl;
          }, true);

          // mark installed to avoid duplicate listeners after subsequent loads
          win.__doxydochub_nav_listener_installed = true;
        }
      } catch (e) { /* ignore */ }

      // Make forms submit inside iframe
      try {
        doc.querySelectorAll("form").forEach(form => form.setAttribute("target", "_self"));
      } catch (e) { /* ignore */ }

    } catch (err) {
      // Accessing iframe content failed — probably cross-origin. Log once.
      console.warn("DoxyDocHub: cannot access iframe content (cross-origin?), navigation won't be intercepted.", err);
      // If cross-origin, we can't force links — consider opening in new tab instead.
    } finally {
      // Hide loader and show iframe (we do this regardless — if content not accessible it's still loaded)
      loader.style.display = "none";
      iframe.classList.remove("hidden");
    }
  });

}

// Helper to get/set expanded items
function getExpandedItems() {
    return JSON.parse(localStorage.getItem("expandedTreeItems") || "[]");
}
function setExpandedItems(ids) {
    localStorage.setItem("expandedTreeItems", JSON.stringify(ids));
}
function setSelectedProject(id) {
    localStorage.setItem("selectedProjectId", id);
}
function getSelectedProject() {
    return localStorage.getItem("selectedProjectId");
}
