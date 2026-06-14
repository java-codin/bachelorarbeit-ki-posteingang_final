(() => {
  const ALL_FILTER = "__all__";
  const views = Array.from(document.querySelectorAll("[data-view]"));
  const navItems = Array.from(document.querySelectorAll("[data-view-target]"));
  const versionButtons = () => Array.from(document.querySelectorAll("[data-version]"));
  const profileButtons = () => Array.from(document.querySelectorAll("[data-profile]"));
  const versionPanels = () => Array.from(document.querySelectorAll("[data-version-panel]"));
  const versionToolbars = Array.from(document.querySelectorAll(".version-toolbar"));
  const profileToolbars = Array.from(document.querySelectorAll(".profile-toolbar"));
  const availabilityElement = document.getElementById("view-version-availability");
  const viewVersionAvailability = availabilityElement
    ? JSON.parse(availabilityElement.textContent || "{}")
    : {};
  const profileAvailabilityElement = document.getElementById("view-profile-availability");
  const viewProfileAvailability = profileAvailabilityElement
    ? JSON.parse(profileAvailabilityElement.textContent || "{}")
    : {};
  const allVersions = Array.from(new Set(
    versionButtons()
      .map((button) => button.dataset.version)
      .filter((version) => version && version !== ALL_FILTER)
  ));
  const allProfiles = Array.from(new Set(
    profileButtons()
      .map((button) => button.dataset.profile)
      .filter((profile) => profile && profile !== ALL_FILTER)
  ));
  let currentView = "overview";
  let activeVersion = document.querySelector(".version-pill.is-active")?.dataset.version
    || document.querySelector("[data-version]")?.dataset.version;
  let activeProfile = document.querySelector(".profile-pill.is-active")?.dataset.profile
    || document.querySelector("[data-profile]")?.dataset.profile
    || "";

  function availableVersions(target) {
    return viewVersionAvailability[target] || allVersions;
  }

  function availableProfiles(target) {
    return viewProfileAvailability[target] || allProfiles;
  }

  function latestAvailableVersion(target) {
    const available = availableVersions(target);
    return [...allVersions].reverse().find((version) => available.includes(version)) || null;
  }

  function updateVersionAvailability(target) {
    const available = new Set(availableVersions(target));
    const availableProfileSet = new Set(availableProfiles(target));
    const hideSelector = target === "downloads";

    versionToolbars.forEach((toolbar) => {
      toolbar.classList.toggle("is-placeholder", hideSelector);
      toolbar.setAttribute("aria-hidden", String(hideSelector));
    });

    profileToolbars.forEach((toolbar) => {
      toolbar.classList.toggle("is-placeholder", hideSelector || allProfiles.length === 0);
      toolbar.setAttribute("aria-hidden", String(hideSelector || allProfiles.length === 0));
    });

    profileButtons().forEach((button) => {
      const disabled = button.dataset.profile !== ALL_FILTER && !availableProfileSet.has(button.dataset.profile);
      button.disabled = disabled;
      button.setAttribute("aria-disabled", String(disabled));
      button.classList.toggle("is-unavailable", disabled);
    });

    if (
      activeProfile !== ALL_FILTER
      && activeProfile
      && !availableProfileSet.has(activeProfile)
    ) {
      setProfile(availableProfiles(target)[0] || ALL_FILTER);
    }

    versionButtons().forEach((button) => {
      const disabled = button.dataset.version !== ALL_FILTER && !available.has(button.dataset.version);
      button.disabled = disabled;
      button.setAttribute("aria-disabled", String(disabled));
      button.classList.toggle("is-unavailable", disabled);
    });

    const nextVersion = latestAvailableVersion(target);
    if (nextVersion && activeVersion !== ALL_FILTER && !available.has(activeVersion)) {
      setVersion(nextVersion, true);
    }

    if (!nextVersion) {
      versionButtons().forEach((button) => button.classList.remove("is-active"));
      versionPanels().forEach((panel) => {
        panel.hidden = true;
      });
      return;
    }

    updatePanels();
  }

  function updatePanels() {
    const available = new Set(availableVersions(currentView));
    versionPanels().forEach((panel) => {
      const panelVersion = panel.dataset.versionPanel;
      const versionMatches = activeVersion === ALL_FILTER
        ? panelVersion === ALL_FILTER || panel.dataset.versionAllPanel === "true"
        : panelVersion === activeVersion;
      const panelProfile = panel.dataset.profilePanel || "";
      const profileMatches = activeProfile === ALL_FILTER
        ? panelProfile === ALL_FILTER || !panelProfile || panel.dataset.profileAllPanel === "true"
        : !panelProfile
        || !activeProfile
        || panelProfile === activeProfile;
      panel.hidden = !(versionMatches && profileMatches);
    });
  }

  function showView(target) {
    currentView = target;
    views.forEach((view) => {
      const active = view.dataset.view === target;
      view.hidden = !active;
      view.classList.toggle("is-active", active);
    });

    navItems.forEach((item) => {
      item.classList.toggle("is-active", item.dataset.viewTarget === target);
    });

    updateVersionAvailability(target);
  }

  function setVersion(version, force = false) {
    if (!force && version !== ALL_FILTER && !availableVersions(currentView).includes(version)) {
      return;
    }

    activeVersion = version;
    versionButtons().forEach((button) => {
      button.classList.toggle("is-active", button.dataset.version === version);
    });

    updatePanels();
  }

  function setProfile(profile) {
    activeProfile = profile || "";
    profileButtons().forEach((button) => {
      button.classList.toggle("is-active", button.dataset.profile === activeProfile);
    });
    updatePanels();
  }

  function numericValue(cell) {
    const raw = cell.dataset.sortValue || cell.textContent.trim();
    const normalized = raw.replace(",", ".").replace("%", "").trim();

    if (!normalized || normalized === "-" || normalized.includes("/") || normalized.toLowerCase() === "nicht erhoben") {
      return null;
    }

    const number = Number(normalized);
    return Number.isFinite(number) ? number : null;
  }

  function dataRows(table) {
    return Array.from(table.tBodies[0]?.rows || [])
      .filter((row) => !row.classList.contains("summary-row"));
  }

  function summaryRows(table) {
    return Array.from(table.tBodies[0]?.rows || [])
      .filter((row) => row.classList.contains("summary-row"));
  }

  function resetTable(table) {
    const tbody = table.tBodies[0];
    if (!tbody) return;

    const rows = dataRows(table);
    const summaries = summaryRows(table);

    rows
      .sort((left, right) => Number(left.dataset.originalIndex) - Number(right.dataset.originalIndex))
      .forEach((row) => tbody.appendChild(row));

    summaries.forEach((row) => tbody.appendChild(row));
  }

  function parseFrequencyText(text) {
    const match = text.trim().match(/^(\d+)\s*\/\s*([\d.,]+)\s*%$/);
    if (!match) return null;

    const absolute = Number(match[1]);
    const relative = Number(match[2].replace(",", "."));

    if (!Number.isFinite(absolute) || !Number.isFinite(relative)) {
      return null;
    }

    return { absolute, relative };
  }

  function initializeFrequencyTables() {
    document.querySelectorAll(".frequency-table td").forEach((cell) => {
      const parsed = parseFrequencyText(cell.textContent);
      if (!parsed) return;

      cell.dataset.frequencyAbsolute = String(parsed.absolute);
      cell.dataset.frequencyRelative = String(parsed.relative);
      cell.textContent = String(parsed.absolute);
      cell.dataset.sortValue = String(parsed.absolute);
    });

    document.querySelectorAll("[data-frequency-label-absolute]").forEach((header) => {
      const label = header.querySelector(".header-label");
      if (label) {
        label.textContent = header.dataset.frequencyLabelAbsolute;
      }
    });
  }

  function setFrequencyMode(view, mode) {
    view.querySelectorAll(".frequency-button").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.frequencyMode === mode);
    });

    view.querySelectorAll("[data-frequency-label-absolute]").forEach((header) => {
      const label = header.querySelector(".header-label");
      if (!label) return;

      label.textContent = mode === "relative"
        ? header.dataset.frequencyLabelRelative
        : header.dataset.frequencyLabelAbsolute;
    });

    view.querySelectorAll(".frequency-table td[data-frequency-absolute]").forEach((cell) => {
      if (mode === "relative") {
        cell.textContent = `${Number(cell.dataset.frequencyRelative).toFixed(1)}%`;
        cell.dataset.sortValue = cell.dataset.frequencyRelative;
      } else {
        cell.textContent = cell.dataset.frequencyAbsolute;
        cell.dataset.sortValue = cell.dataset.frequencyAbsolute;
      }
    });

    view.querySelectorAll(".sortable-table").forEach((table) => {
      resetTable(table);
      table.querySelectorAll("th").forEach((header) => header.removeAttribute("aria-sort"));
    });
  }

  function initializeSortableTables() {
    document.querySelectorAll(".sortable-table").forEach((table) => {
      const headers = Array.from(table.tHead?.rows[0]?.cells || []);
      dataRows(table).forEach((row, index) => {
        row.dataset.originalIndex = String(index);
      });

      headers.forEach((header, columnIndex) => {
        const button = header.querySelector(".sort-button");
        const values = dataRows(table)
          .map((row) => numericValue(row.cells[columnIndex]))
          .filter((value) => value !== null);
        const sortable = values.length > 0;

        header.classList.toggle("is-numeric-sortable", sortable);
        header.classList.toggle("is-not-sortable", !sortable);

        if (button) {
          button.disabled = !sortable;
          button.setAttribute("aria-disabled", String(!sortable));
          button.title = sortable
            ? "Numerisch sortieren; dritter Klick setzt die Reihenfolge zurück"
            : "Diese Spalte enthält keine numerisch sortierbaren Werte";
        }
      });
    });
  }

  function sortTable(table, columnIndex, direction) {
    const tbody = table.tBodies[0];
    if (!tbody) return;

    if (direction === "none") {
      resetTable(table);
      return;
    }

    const rows = dataRows(table);
    const summaries = summaryRows(table);
    rows.sort((left, right) => {
      const leftValue = numericValue(left.cells[columnIndex]);
      const rightValue = numericValue(right.cells[columnIndex]);

      if (leftValue === null && rightValue === null) {
        return Number(left.dataset.originalIndex) - Number(right.dataset.originalIndex);
      }

      if (leftValue === null) return 1;
      if (rightValue === null) return -1;

      return direction === "ascending" ? leftValue - rightValue : rightValue - leftValue;
    });

    rows.forEach((row) => tbody.appendChild(row));
    summaries.forEach((row) => tbody.appendChild(row));
  }

  navItems.forEach((item) => {
    item.addEventListener("click", () => showView(item.dataset.viewTarget));
  });

  document.addEventListener("click", (event) => {
    const versionButton = event.target.closest("[data-version]");
    if (versionButton) {
      if (versionButton.disabled) return;
      setVersion(versionButton.dataset.version);
      return;
    }

    const profileButton = event.target.closest("[data-profile]");
    if (profileButton) {
      if (profileButton.disabled) return;
      setProfile(profileButton.dataset.profile);
      return;
    }

    const frequencyButton = event.target.closest("[data-frequency-mode]");
    if (frequencyButton) {
      const view = frequencyButton.closest("[data-view]");
      if (view) {
        setFrequencyMode(view, frequencyButton.dataset.frequencyMode);
      }
      return;
    }

    const toggleButton = event.target.closest("[data-toggle-target]");
    if (toggleButton) {
      const target = document.getElementById(toggleButton.dataset.toggleTarget);
      if (!target) return;

      const willOpen = target.hidden;
      target.hidden = !willOpen;
      toggleButton.setAttribute("aria-expanded", String(willOpen));

      if (willOpen) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      return;
    }

    const sortButton = event.target.closest(".sort-button");
    if (!sortButton) return;

    const header = sortButton.closest("th");
    const table = sortButton.closest("table");
    if (!header || !table) return;
    if (sortButton.disabled || !header.classList.contains("is-numeric-sortable")) return;

    const headers = Array.from(header.parentElement.children);
    const columnIndex = headers.indexOf(header);
    const currentDirection = header.getAttribute("aria-sort");
    const nextDirection = currentDirection === "ascending"
      ? "descending"
      : currentDirection === "descending"
        ? "none"
        : "ascending";

    headers.forEach((cell) => cell.removeAttribute("aria-sort"));
    if (nextDirection !== "none") {
      header.setAttribute("aria-sort", nextDirection);
    }
    sortTable(table, columnIndex, nextDirection);
  });

  if (activeVersion) {
    setVersion(activeVersion, true);
  }
  if (activeProfile) {
    setProfile(activeProfile);
  }

  initializeFrequencyTables();
  initializeSortableTables();
  showView("overview");
})();
