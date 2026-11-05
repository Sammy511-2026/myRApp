(() => {
  const formsetRows = new Map();

  const registerRow = (row) => {
    const deleteCheckbox = row?.querySelector('input[type="checkbox"][name$="-DELETE"]');
    if (deleteCheckbox) {
      formsetRows.set(deleteCheckbox.name, { row, deleteCheckbox });
    }
  };

  document.querySelectorAll("[data-formset-row]").forEach(registerRow);

  document.querySelectorAll("[data-add-formset]").forEach((button) => {
    button.addEventListener("click", () => {
      const prefix = button.dataset.addFormset;
      const templateId = button.dataset.template;
      const group = button.closest("[data-formset-group]");
      const totalForms = group?.querySelector(`input[name="${prefix}-TOTAL_FORMS"]`);
      const formsetBody = group?.querySelector(`[data-formset-body="${prefix}"]`);
      const rowTemplate = group?.querySelector(`#${templateId}`);

      if (!totalForms || !formsetBody || !rowTemplate) {
        console.error(`Unable to add ${prefix} form: formset controls are missing.`);
        return;
      }

      const index = Number(totalForms.value);
      if (!Number.isInteger(index) || index < 0) {
        console.error(`Unable to add ${prefix} form: invalid form index.`);
        return;
      }

      const fragment = rowTemplate.content.cloneNode(true);
      const elements = fragment.querySelectorAll("*");
      elements.forEach((element) => {
        Array.from(element.attributes).forEach((attribute) => {
          attribute.value = attribute.value.replace(/__prefix__/g, String(index));
        });
      });
      const newRow = fragment.querySelector("[data-formset-row]");
      if (!newRow) {
        console.error(`Unable to add ${prefix} form: row template is empty.`);
        return;
      }

      const tableBody = formsetBody.querySelector("tbody") || formsetBody;
      tableBody.append(fragment);
      totalForms.value = String(index + 1);
      registerRow(newRow);
    });
  });

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const removeButton = target?.closest(".formset-remove");
    if (removeButton) {
      const row = removeButton.closest("[data-formset-row]");
      const deleteCheckbox = row?.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (!row || !deleteCheckbox) {
        console.error("Unable to remove form: delete checkbox is missing.");
        return;
      }

      const prefix = deleteCheckbox.name.split("-")[0];
      const group = removeButton.closest("[data-formset-group]");
      const restorePanel = group?.querySelector(`[data-removed-forms="${prefix}"]`);
      if (!restorePanel) {
        console.error(`Unable to remove ${prefix} form: restore panel is missing.`);
        return;
      }

      if (deleteCheckbox.checked) {
        return;
      }
      deleteCheckbox.checked = true;
      row.hidden = true;

      const restoreButton = document.createElement("button");
      restoreButton.className = "formset-restore";
      restoreButton.type = "button";
      restoreButton.dataset.restoreForm = deleteCheckbox.name;
      restoreButton.textContent = "Restore removed record";
      restorePanel.append(restoreButton);
      restorePanel.hidden = false;
      return;
    }

    const restoreButton = target?.closest(".formset-restore");
    if (!restoreButton) {
      return;
    }

    const form = formsetRows.get(restoreButton.dataset.restoreForm);
    if (!form) {
      return;
    }

    form.deleteCheckbox.checked = false;
    form.row.hidden = false;
    restoreButton.remove();

    const restorePanel = restoreButton.closest("[data-removed-forms]");
    if (restorePanel && !restorePanel.querySelector(".formset-restore")) {
      restorePanel.hidden = true;
    }
  });

  document.querySelectorAll("[data-formset-row] input[name$='-DELETE']:checked").forEach((checkbox) => {
    const form = formsetRows.get(checkbox.name);
    const prefix = checkbox.name.split("-")[0];
    const restorePanel = checkbox.closest("[data-formset-group]")?.querySelector(
      `[data-removed-forms="${prefix}"]`
    );
    if (!form || !restorePanel) {
      return;
    }

    form.row.hidden = true;
    const restoreButton = document.createElement("button");
    restoreButton.className = "formset-restore";
    restoreButton.type = "button";
    restoreButton.dataset.restoreForm = checkbox.name;
    restoreButton.textContent = "Restore removed record";
    restorePanel.append(restoreButton);
    restorePanel.hidden = false;
  });
})();
