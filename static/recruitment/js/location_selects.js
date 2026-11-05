(() => {
  const form = document.querySelector("form[data-districts-url]");
  if (!form) return;

  const provinceSelect = form.querySelector('[name="province"]');
  const districtSelect = form.querySelector('[name="district"]');
  if (!provinceSelect || !districtSelect) return;

  const status = document.createElement("span");
  status.className = "location-select-status";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  districtSelect.insertAdjacentElement("afterend", status);
  let activeRequest;

  async function loadDistricts(preserveSelection) {
    if (activeRequest) activeRequest.abort();
    activeRequest = new AbortController();
    const previousSelection = preserveSelection ? districtSelect.value : "";
    districtSelect.replaceChildren(new Option("Select a district", ""));
    status.textContent = "";

    if (!provinceSelect.value) {
      districtSelect.disabled = true;
      return;
    }

    districtSelect.disabled = true;
    status.textContent = "Loading districts…";

    try {
      const url = new URL(form.dataset.districtsUrl, window.location.origin);
      url.searchParams.set("province_id", provinceSelect.value);
      const response = await fetch(url, {
        headers: { Accept: "application/json" },
        signal: activeRequest.signal,
      });
      if (!response.ok) {
        throw new Error(`District lookup failed (${response.status}).`);
      }

      const data = await response.json();
      if (data.districts.length) {
        const group = document.createElement("optgroup");
        group.label = data.province;
        for (const district of data.districts) {
          group.append(new Option(district.name, district.id));
        }
        districtSelect.append(group);
        districtSelect.disabled = false;
        districtSelect.value = previousSelection;
        status.textContent = "";
      } else {
        status.textContent = "No districts are configured for this province.";
      }
    } catch (error) {
      if (error.name === "AbortError") return;
      status.textContent = "Districts could not be loaded. Please select the province again to retry.";
      console.error(error);
    }
  }

  provinceSelect.addEventListener("change", () => loadDistricts(false));
  loadDistricts(true);
})();
