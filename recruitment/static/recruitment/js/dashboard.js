// Collapsible user menu
(function () {
    const btn = document.getElementById('userMenuBtn');
    const panel = document.getElementById('userMenuPanel');
    if (!btn || !panel) return;

    function openMenu() { panel.hidden = false; btn.setAttribute('aria-expanded', 'true'); }
    function closeMenu() { panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); }
    function toggleMenu() { (panel.hidden ? openMenu : closeMenu)(); }

    btn.addEventListener('click', (e) => { e.preventDefault(); toggleMenu(); });

    document.addEventListener('click', (e) => {
        if (!panel.hidden && !panel.contains(e.target) && !btn.contains(e.target)) closeMenu();
    });

    panel.addEventListener('click', (e) => {
        const a = e.target.closest('a[data-close]'); if (a) closeMenu();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !panel.hidden) closeMenu();
    });
})();

// Avatar change + Cropper.js flow
(function () {
    const changeBtn = document.getElementById('changePhotoBtn');
    const deleteForm = document.getElementById('deletePhotoForm');
    const photoInput = document.getElementById('photoInput');
    const profileForm = document.getElementById('profileForm');
    const croppedField = document.getElementById('croppedPhoto');

    const modal = document.getElementById('cropModal');
    const cropImg = document.getElementById('cropImage');
    const closeEls = modal ? modal.querySelectorAll('[data-close]') : [];
    const zoomInBtn = document.getElementById('zoomInBtn');
    const zoomOutBtn = document.getElementById('zoomOutBtn');
    const rotateBtn = document.getElementById('rotateBtn');
    const resetBtn = document.getElementById('resetBtn');
    const saveBtn = document.getElementById('cropSaveBtn');

    let cropper = null;

    function openModal() { modal.setAttribute('aria-hidden', 'false'); }
    function closeModal() {
        modal.setAttribute('aria-hidden', 'true');
        if (cropper) { cropper.destroy(); cropper = null; }
        cropImg.removeAttribute('src');
    }

    if (changeBtn && photoInput && modal) {
        changeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            photoInput.click();
        });

        photoInput.addEventListener('change', () => {
            const file = photoInput.files && photoInput.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = () => {
                cropImg.src = reader.result;
                openModal();
                // init cropper when image has loaded
                cropImg.onload = () => {
                    cropper = new Cropper(cropImg, {
                        aspectRatio: 1,
                        viewMode: 1,
                        dragMode: 'move',
                        background: false,
                        autoCropArea: 1,
                    });
                };
            };
            reader.readAsDataURL(file);
        });
    }

    // Controls
    if (zoomInBtn) zoomInBtn.addEventListener('click', () => { if (cropper) cropper.zoom(0.1); });
    if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => { if (cropper) cropper.zoom(-0.1); });
    if (rotateBtn) rotateBtn.addEventListener('click', () => { if (cropper) cropper.rotate(90); });
    if (resetBtn) resetBtn.addEventListener('click', () => { if (cropper) cropper.reset(); });

    // Close modal
    closeEls.forEach(el => el.addEventListener('click', closeModal));
    if (modal) modal.addEventListener('click', (e) => { if (e.target.classList.contains('modal__backdrop')) closeModal(); });

    // Save cropped -> data URL -> hidden field -> submit
    if (saveBtn) {
        saveBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (!cropper) return;

            const canvas = cropper.getCroppedCanvas({ width: 600, height: 600 }); // decent quality square
            if (!canvas) return;

            const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
            croppedField.value = dataUrl;
            closeModal();

            // Submit profile form with new cropped image
            if (profileForm) profileForm.submit();
        });
    }

    // If user presses delete icon without existing photo, let the view handle it elegantly
    if (deleteForm) {
        deleteForm.addEventListener('submit', () => {
            // no-op; server will show “No profile photo to remove.” if none
        });
    }
})();
