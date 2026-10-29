(() => {
  const form = document.getElementById('upload-form');
  if (!form) return;

  const modelReady = form.dataset.modelReady === 'true';
  const modeField = document.getElementById('upload-mode');
  const modeButtons = [...document.querySelectorAll('[data-upload-mode]')];
  const modePanels = [...document.querySelectorAll('[data-mode-content]')];
  const singleInput = document.getElementById('leaf-image');
  const multiInput = document.getElementById('crop-images');
  const dropZone = document.getElementById('drop-zone');
  const multiDropZone = document.getElementById('multi-drop-zone');
  const placeholder = document.getElementById('upload-placeholder');
  const previewWrap = document.getElementById('preview-wrap');
  const preview = document.getElementById('image-preview');
  const fileName = document.getElementById('file-name');
  const fileSize = document.getElementById('file-size');
  const multiPlaceholder = document.getElementById('multi-upload-placeholder');
  const multiPreviewGrid = document.getElementById('multi-preview-grid');
  const clearMultiButton = document.getElementById('clear-multi-photos');
  const submitButton = document.getElementById('detect-button');
  const progress = document.getElementById('progress-message');
  let currentMode = 'single';

  const MAX_FILE_SIZE = 8 * 1024 * 1024;
  const MAX_FILES = 5;
  const allowedExtensions = ['jpg', 'jpeg', 'png', 'webp'];

  const readableSize = (bytes) => bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

  const isAllowedImage = (file) => {
    const extension = (file.name.split('.').pop() || '').toLowerCase();
    const allowedMime = ['image/jpeg', 'image/png', 'image/webp'];
    return allowedExtensions.includes(extension) && (!file.type || allowedMime.includes(file.type));
  };

  const setSubmitLabel = () => {
    if (currentMode === 'multiple') {
      const count = multiInput?.files?.length || 0;
      submitButton.innerHTML = `<span>Analyse ${count || 'selected'} photo${count === 1 ? '' : 's'}</span><span aria-hidden="true">→</span>`;
    } else {
      submitButton.innerHTML = '<span>Analyse selected photo</span><span aria-hidden="true">→</span>';
    }
  };

  const setMode = (mode) => {
    currentMode = mode;
    modeField.value = mode;
    modeButtons.forEach((button) => {
      const active = button.dataset.uploadMode === mode;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    modePanels.forEach((panel) => {
      panel.hidden = panel.dataset.modeContent !== mode;
    });
    if (singleInput) singleInput.disabled = !modelReady || mode !== 'single';
    if (multiInput) multiInput.disabled = !modelReady || mode !== 'multiple';
    if (dropZone) dropZone.classList.toggle('drop-zone-disabled', !modelReady || mode !== 'single');
    if (multiDropZone) multiDropZone.classList.toggle('drop-zone-disabled', !modelReady || mode !== 'multiple');
    setSubmitLabel();
  };

  const showSingleFile = (file) => {
    if (!file || !singleInput || singleInput.disabled) return;
    if (!isAllowedImage(file)) {
      alert('Please choose a JPG, PNG, or WEBP image.');
      singleInput.value = '';
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      alert('Please choose an image that is 8 MB or smaller.');
      singleInput.value = '';
      return;
    }
    const url = URL.createObjectURL(file);
    preview.src = url;
    preview.onload = () => URL.revokeObjectURL(url);
    fileName.textContent = file.name;
    fileSize.textContent = readableSize(file.size);
    placeholder.hidden = true;
    previewWrap.hidden = false;
    dropZone.classList.add('has-image');
    setSubmitLabel();
  };

  const assignFiles = (input, files) => {
    try {
      const transfer = new DataTransfer();
      files.forEach((file) => transfer.items.add(file));
      input.files = transfer.files;
      return true;
    } catch (_error) {
      return false;
    }
  };

  const renderMultiFiles = () => {
    if (!multiInput || !multiPreviewGrid) return;
    const files = [...multiInput.files];
    multiPreviewGrid.replaceChildren();
    multiPreviewGrid.hidden = files.length === 0;
    multiPlaceholder.hidden = files.length > 0;
    clearMultiButton.hidden = files.length === 0;

    files.forEach((file, index) => {
      const card = document.createElement('div');
      card.className = 'multi-photo-card';
      const img = document.createElement('img');
      img.alt = `Selected crop photo ${index + 1}`;
      img.src = URL.createObjectURL(file);
      img.onload = () => URL.revokeObjectURL(img.src);
      const meta = document.createElement('div');
      meta.className = 'multi-photo-meta';
      const name = document.createElement('strong');
      name.textContent = file.name;
      name.title = file.name;
      const size = document.createElement('small');
      size.textContent = readableSize(file.size);
      meta.append(name, size);
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'remove-photo-button';
      remove.setAttribute('aria-label', `Remove ${file.name}`);
      remove.textContent = '×';
      remove.addEventListener('click', () => {
        const remaining = [...multiInput.files].filter((_, fileIndex) => fileIndex !== index);
        if (assignFiles(multiInput, remaining)) {
          renderMultiFiles();
          setSubmitLabel();
        }
      });
      card.append(img, meta, remove);
      multiPreviewGrid.append(card);
    });
    setSubmitLabel();
  };

  const validateMultiFiles = (files) => {
    if (files.length > MAX_FILES) {
      alert('You can add up to 5 photos at a time.');
      return false;
    }
    for (const file of files) {
      if (!isAllowedImage(file)) {
        alert(`“${file.name}” is not a supported image. Use JPG, PNG, or WEBP.`);
        return false;
      }
      if (file.size > MAX_FILE_SIZE) {
        alert(`“${file.name}” is larger than 8 MB. Choose a smaller photo.`);
        return false;
      }
    }
    return true;
  };

  const addDragDrop = (zone, input, isMultiple) => {
    if (!zone || !input) return;
    ['dragenter', 'dragover'].forEach((eventName) => {
      zone.addEventListener(eventName, (event) => {
        event.preventDefault();
        if (!input.disabled) zone.classList.add('drag-active');
      });
    });
    ['dragleave', 'drop'].forEach((eventName) => {
      zone.addEventListener(eventName, (event) => {
        event.preventDefault();
        zone.classList.remove('drag-active');
      });
    });
    zone.addEventListener('drop', (event) => {
      if (input.disabled) return;
      const dropped = [...(event.dataTransfer?.files || [])];
      if (dropped.length === 0) return;
      if (isMultiple) {
        const merged = [...input.files, ...dropped];
        // Keep each selection unique by name and size.
        const unique = merged.filter((file, index, all) =>
          all.findIndex((other) => other.name === file.name && other.size === file.size) === index
        );
        if (!validateMultiFiles(unique)) return;
        if (assignFiles(input, unique)) renderMultiFiles();
        else alert('Your browser could not add dropped files. Please use “browse files” instead.');
      } else {
        const file = dropped[0];
        if (assignFiles(input, [file])) showSingleFile(file);
        else alert('Your browser could not add the dropped file. Please use “browse files” instead.');
      }
    });
  };

  modeButtons.forEach((button) => {
    button.addEventListener('click', () => setMode(button.dataset.uploadMode));
  });
  singleInput?.addEventListener('change', (event) => showSingleFile(event.target.files[0]));
  multiInput?.addEventListener('change', () => {
    const files = [...multiInput.files];
    if (!validateMultiFiles(files)) {
      multiInput.value = '';
    }
    renderMultiFiles();
  });
  clearMultiButton?.addEventListener('click', () => {
    multiInput.value = '';
    renderMultiFiles();
  });
  addDragDrop(dropZone, singleInput, false);
  addDragDrop(multiDropZone, multiInput, true);

  form.addEventListener('submit', (event) => {
    const selectedCount = currentMode === 'multiple'
      ? (multiInput?.files?.length || 0)
      : (singleInput?.files?.length || 0);
    if (selectedCount === 0) {
      event.preventDefault();
      alert(currentMode === 'multiple'
        ? 'Please add at least one crop photo first.'
        : 'Please select a leaf photo first.');
      return;
    }
    if (currentMode === 'multiple' && !validateMultiFiles([...multiInput.files])) {
      event.preventDefault();
      return;
    }
    submitButton.disabled = true;
    submitButton.innerHTML = '<span>Analysing…</span><span class="spinner spinner-light"></span>';
    if (progress) progress.hidden = false;
  });

  document.querySelectorAll('.flash-close').forEach((button) => {
    button.addEventListener('click', () => button.closest('.flash')?.remove());
  });

  setMode('single');
})();
