/**
 * HarmoNiq - YouTube MP3 & Shazam Auto-Tagger JavaScript Engine
 */

document.addEventListener("DOMContentLoaded", () => {
    // State management
    const state = {
        currentDir: "",
        autoShazam: true,
        quality: "320",
        activeWs: null,
        recentDownloads: [],
        localFiles: [],
        currentEditingFile: null,
        currentTaskId: null
    };

    // DOM Elements
    const elements = {
        navButtons: document.querySelectorAll(".nav-btn"),
        tabContents: document.querySelectorAll(".tab-content"),
        sidebarPathDisplay: document.getElementById("sidebar-path-display"),
        sidebarChangeDirBtn: document.getElementById("sidebar-change-dir-btn"),
        
        // Download Tab
        ytUrlInput: document.getElementById("yt-url-input"),
        startDownloadBtn: document.getElementById("start-download-btn"),
        autoShazamCheck: document.getElementById("auto-shazam-check"),
        qualitySelect: document.getElementById("quality-select"),
        customDirInput: document.getElementById("custom-dir-input"),
        btnBrowseDir: document.getElementById("btn-browse-dir"),
        
        // Download Status Card
        downloadStatusCard: document.getElementById("download-status-card"),
        statusSpinner: document.getElementById("status-spinner"),
        statusTitleText: document.getElementById("status-title-text"),
        statusPercent: document.getElementById("status-percent"),
        statusProgressFill: document.getElementById("status-progress-fill"),
        statusDetailMsg: document.getElementById("status-detail-msg"),
        statusSpeedEta: document.getElementById("status-speed-eta"),
        btnCancelDownload: document.getElementById("btn-cancel-download"),
        songResultCard: document.getElementById("song-result-card"),
        resCoverImg: document.getElementById("res-cover-img"),
        resShazamBadge: document.getElementById("res-shazam-badge"),
        resTitle: document.getElementById("res-title"),
        resArtist: document.getElementById("res-artist"),
        resAlbum: document.getElementById("res-album"),
        resYear: document.getElementById("res-year"),
        resGenre: document.getElementById("res-genre"),
        resPlayBtn: document.getElementById("res-play-btn"),
        resEditBtn: document.getElementById("res-edit-btn"),
        resOpenFolderBtn: document.getElementById("res-open-folder-btn"),
        recentDownloadsGrid: document.getElementById("recent-downloads-grid"),
        
        // Shazam & Tag Editor Tab
        mp3DropZone: document.getElementById("mp3-drop-zone"),
        filePickerInput: document.getElementById("file-picker-input"),
        btnSelectFile: document.getElementById("btn-select-file"),
        localFilesSelect: document.getElementById("local-files-select"),
        btnLoadSelectedFile: document.getElementById("btn-load-selected-file"),
        btnRunShazamRecognition: document.getElementById("btn-run-shazam-recognition"),
        tagEditorForm: document.getElementById("tag-editor-form"),
        tagFilePath: document.getElementById("tag-file-path"),
        tagCoverUrl: document.getElementById("tag-cover-url"),
        editorCoverPreview: document.getElementById("editor-cover-preview"),
        coverFileInput: document.getElementById("cover-file-input"),
        shazamStatusBadge: document.getElementById("shazam-status-badge"),
        tagTitle: document.getElementById("tag-title"),
        tagArtist: document.getElementById("tag-artist"),
        tagAlbum: document.getElementById("tag-album"),
        tagYear: document.getElementById("tag-year"),
        tagGenre: document.getElementById("tag-genre"),
        tagLyrics: document.getElementById("tag-lyrics"),
        btnSaveTags: document.getElementById("btn-save-tags"),
        
        // Files Tab
        btnRefreshFiles: document.getElementById("btn-refresh-files"),
        btnOpenDirExplorer: document.getElementById("btn-open-dir-explorer"),
        filesSearchInput: document.getElementById("files-search-input"),
        filesTableBody: document.getElementById("files-table-body"),
        
        // Settings Tab
        settingsForm: document.getElementById("settings-form"),
        settingsDirInput: document.getElementById("settings-dir-input"),
        btnSettingsBrowse: document.getElementById("btn-settings-browse"),
        shortcutPillsContainer: document.getElementById("shortcut-pills-container"),
        settingsAutoShazam: document.getElementById("settings-auto-shazam"),
        
        // Sticky Audio Player
        stickyPlayer: document.getElementById("sticky-player"),
        playerCover: document.getElementById("player-cover"),
        playerTitle: document.getElementById("player-title"),
        playerArtist: document.getElementById("player-artist"),
        mainAudioElement: document.getElementById("main-audio-element"),
        playerCloseBtn: document.getElementById("player-close-btn"),
        toastContainer: document.getElementById("toast-container")
    };

    // --- Initialization ---
    init();

    async function init() {
        setupTabNavigation();
        await loadConfig();
        await loadFilesList();
        setupEventListeners();
    }

    function setupEventListeners() {
        elements.sidebarChangeDirBtn.addEventListener("click", () => {
            document.querySelector('.nav-btn[data-tab="settings-tab"]').click();
        });

        // Abre el selector de carpetas NATIVO del sistema (vía puente Qt).
        // Si se ejecuta en un navegador normal (desarrollo), cae al prompt.
        function pickDirectory(current) {
            return new Promise((resolve) => {
                if (window.hqBackend && window.hqBackend.selectDirectory) {
                    window.hqBackend.selectDirectory(current || "", (path) => resolve(path || null));
                } else {
                    resolve(prompt("Introduce la ruta completa de la carpeta en tu PC:", current) || null);
                }
            });
        }

        elements.btnBrowseDir.addEventListener("click", async () => {
            const newDir = await pickDirectory(state.currentDir);
            if (newDir) {
                updateCurrentDirectory(newDir);
            }
        });

        elements.btnSettingsBrowse.addEventListener("click", async () => {
            const newDir = await pickDirectory(elements.settingsDirInput.value);
            if (newDir) {
                elements.settingsDirInput.value = newDir;
            }
        });

        if (elements.btnCancelDownload) {
            elements.btnCancelDownload.addEventListener("click", async () => {
                if (state.currentTaskId) {
                    try {
                        const res = await fetch(`/api/cancel/${state.currentTaskId}`, { method: "POST" });
                        const data = await res.json();
                        if (data.success) {
                            showToast("Cancelando descarga...", "info");
                            elements.btnCancelDownload.style.display = "none";
                        }
                    } catch (err) {
                        console.error(err);
                    }
                }
            });
        }
    }

    // --- Tab Navigation ---
    function setupTabNavigation() {
        elements.navButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                const targetTab = btn.getAttribute("data-tab");
                elements.navButtons.forEach(b => b.classList.remove("active"));
                elements.tabContents.forEach(c => c.classList.remove("active"));
                btn.classList.add("active");
                document.getElementById(targetTab).classList.add("active");

                if (targetTab === "files-tab") {
                    loadFilesList();
                }
            });
        });
    }

    // --- Config Loading & Syncing ---
    async function loadConfig() {
        try {
            const res = await fetch("/api/config");
            const data = await res.json();
            
            state.currentDir = data.download_dir;
            state.autoShazam = data.auto_shazam;
            state.quality = data.quality;
            
            elements.sidebarPathDisplay.textContent = state.currentDir;
            elements.customDirInput.value = state.currentDir;
            elements.settingsDirInput.value = state.currentDir;
            elements.autoShazamCheck.checked = state.autoShazam;
            elements.settingsAutoShazam.checked = state.autoShazam;
            elements.qualitySelect.value = state.quality;

            renderShortcuts(data.shortcuts || []);
        } catch (err) {
            showToast("Error cargando configuración inicial", "error");
        }
    }

    function renderShortcuts(shortcuts) {
        elements.shortcutPillsContainer.innerHTML = "";
        shortcuts.forEach(sc => {
            const pill = document.createElement("button");
            pill.type = "button";
            pill.className = "pill-btn";
            pill.innerHTML = `<i class="fa-solid fa-folder"></i> ${sc.name}`;
            pill.addEventListener("click", () => {
                updateCurrentDirectory(sc.yt_path);
            });
            elements.shortcutPillsContainer.appendChild(pill);
        });
    }

    async function updateCurrentDirectory(newDir) {
        try {
            const res = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    download_dir: newDir,
                    auto_shazam: elements.autoShazamCheck.checked,
                    quality: elements.qualitySelect.value
                })
            });
            const data = await res.json();
            if (data.success) {
                state.currentDir = data.download_dir;
                elements.sidebarPathDisplay.textContent = state.currentDir;
                elements.customDirInput.value = state.currentDir;
                elements.settingsDirInput.value = state.currentDir;
                showToast(`Directorio guardado en: ${state.currentDir}`, "success");
                loadFilesList();
            } else {
                showToast(`Error: ${data.error}`, "error");
            }
        } catch (err) {
            showToast("Error al actualizar directorio", "error");
        }
    }

    // --- Download Process ---
    elements.startDownloadBtn.addEventListener("click", handleStartDownload);
    elements.ytUrlInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleStartDownload();
    });

    async function handleStartDownload() {
        const url = elements.ytUrlInput.value.trim();
        if (!url) {
            showToast("Introduce un enlace de YouTube válido", "error");
            return;
        }

        const targetDir = elements.customDirInput.value.trim() || state.currentDir;
        const autoShazam = elements.autoShazamCheck.checked;
        const quality = elements.qualitySelect.value;

        // Reset UI Status
        elements.downloadStatusCard.classList.remove("hidden");
        elements.songResultCard.classList.add("hidden");
        elements.statusSpinner.classList.remove("hidden");
        elements.statusTitleText.textContent = "Iniciando proceso de descarga...";
        elements.statusPercent.textContent = "0%";
        elements.statusProgressFill.style.width = "0%";
        elements.statusDetailMsg.textContent = "Conectando con YouTube...";
        elements.statusSpeedEta.textContent = "";

        try {
            const res = await fetch("/api/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: url,
                    output_dir: targetDir,
                    auto_shazam: autoShazam,
                    quality: quality
                })
            });
            const data = await res.json();
            if (data.task_id) {
                state.currentTaskId = data.task_id;
                elements.btnCancelDownload.style.display = "inline-flex";
                connectWebSocket(data.task_id);
            } else {
                showToast("No se pudo iniciar la tarea de descarga", "error");
            }
        } catch (err) {
            showToast("Error al conectar con el servidor", "error");
        }
    }

    function connectWebSocket(taskId) {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/progress/${taskId}`;
        
        if (state.activeWs) {
            state.activeWs.close();
        }

        state.activeWs = new WebSocket(wsUrl);

        state.activeWs.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateDownloadProgressUI(data);
        };

        state.activeWs.onerror = () => {
            showToast("Error de conexión en tiempo real", "error");
        };
    }

    function updateDownloadProgressUI(data) {
        if (data.percent !== undefined) {
            elements.statusPercent.textContent = `${data.percent}%`;
            elements.statusProgressFill.style.width = `${data.percent}%`;
        }

        if (data.message) {
            elements.statusDetailMsg.textContent = data.message;
        }

        if (data.step === "downloading") {
            elements.statusTitleText.textContent = data.message.includes("[") ? data.message : "Descargando Audio...";
            if (data.speed && data.eta) {
                const speedMb = (data.speed / (1024 * 1024)).toFixed(2);
                elements.statusSpeedEta.textContent = `${speedMb} MB/s | ETA: ${data.eta}s`;
            }
        } else if (data.step === "shazam") {
            elements.statusTitleText.textContent = data.message.includes("[") ? data.message : "Reconociendo con Shazam...";
            elements.statusSpeedEta.textContent = "Analizando huella acústica";
        } else if (data.step === "tagging") {
            elements.statusTitleText.textContent = data.message.includes("[") ? data.message : "Aplicando Etiquetas ID3...";
            elements.statusSpeedEta.textContent = "Insertando carátula y metadatos";
        } else if (data.step === "item_completed") {
            if (data.file_info) {
                showCompletedSong(data.file_info);
                addRecentDownload(data.file_info);
            }
            showToast("Canción completada", "info");
            loadFilesList();
        } else if (data.step === "completed") {
            elements.statusSpinner.classList.add("hidden");
            elements.btnCancelDownload.style.display = "none";
            elements.statusTitleText.textContent = "¡Proceso completado!";
            elements.statusDetailMsg.textContent = "Todas las tareas han finalizado.";
            elements.statusSpeedEta.textContent = "";

            if (data.file_info) {
                showCompletedSong(data.file_info);
                addRecentDownload(data.file_info);
            }
            showToast("¡Finalizado con éxito!", "success");
            elements.ytUrlInput.value = "";
            loadFilesList();
        } else if (data.step === "error") {
            elements.statusSpinner.classList.add("hidden");
            elements.btnCancelDownload.style.display = "none";
            elements.statusTitleText.textContent = "Error durante el proceso";
            elements.statusDetailMsg.textContent = data.message;
            showToast(`Error: ${data.message}`, "error");
        }
    }

    function showCompletedSong(info) {
        elements.songResultCard.classList.remove("hidden");
        const coverSrc = info.cover_url || `/api/cover-file?path=${encodeURIComponent(info.filepath)}&t=${Date.now()}`;
        elements.resCoverImg.src = coverSrc;
        elements.resTitle.textContent = info.title || info.filename;
        elements.resArtist.textContent = info.artist || "Artista Desconocido";
        elements.resAlbum.textContent = info.album || "Álbum Desconocido";
        elements.resYear.innerHTML = `<i class="fa-regular fa-calendar"></i> ${info.year || "N/A"}`;
        elements.resGenre.innerHTML = `<i class="fa-solid fa-music"></i> ${info.genre || "General"}`;

        if (info.matched_by_shazam) {
            elements.resShazamBadge.classList.remove("hidden");
        } else {
            elements.resShazamBadge.classList.add("hidden");
        }

        // Action Buttons
        elements.resPlayBtn.onclick = () => playAudio(info.filepath, info.title, info.artist, coverSrc);
        elements.resEditBtn.onclick = () => {
            switchToEditorAndLoad(info.filepath);
        };
        elements.resOpenFolderBtn.onclick = () => openFolder(state.currentDir);
    }

    function addRecentDownload(info) {
        state.recentDownloads.unshift(info);
        if (state.recentDownloads.length > 6) state.recentDownloads.pop();
        renderRecentGrid();
    }

    function renderRecentGrid() {
        if (state.recentDownloads.length === 0) {
            elements.recentDownloadsGrid.innerHTML = '<p class="empty-state">No hay descargas en esta sesión aún.</p>';
            return;
        }

        elements.recentDownloadsGrid.innerHTML = "";
        state.recentDownloads.forEach(item => {
            const coverSrc = item.cover_url || `/api/cover-file?path=${encodeURIComponent(item.filepath)}&t=${Date.now()}`;
            const card = document.createElement("div");
            card.className = "recent-card";
            card.innerHTML = `
                <img src="${coverSrc}" alt="Cover">
                <div class="recent-info">
                    <h4>${item.title || item.filename}</h4>
                    <p>${item.artist || 'Artista'}</p>
                </div>
            `;
            card.addEventListener("click", () => {
                playAudio(item.filepath, item.title, item.artist, coverSrc);
            });
            elements.recentDownloadsGrid.appendChild(card);
        });
    }

    // --- Shazam & Tag Editor Tab ---
    elements.btnSelectFile.addEventListener("click", () => elements.filePickerInput.click());
    elements.filePickerInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            uploadAndRecognizeFile(e.target.files[0]);
        }
    });

    // Drag and Drop support
    elements.mp3DropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        elements.mp3DropZone.classList.add("dragover");
    });
    elements.mp3DropZone.addEventListener("dragleave", () => {
        elements.mp3DropZone.classList.remove("dragover");
    });
    elements.mp3DropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        elements.mp3DropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            uploadAndRecognizeFile(e.dataTransfer.files[0]);
        }
    });

    elements.btnLoadSelectedFile.addEventListener("click", () => {
        const filePath = elements.localFilesSelect.value;
        if (filePath) {
            loadTagsIntoEditor(filePath);
        } else {
            showToast("Selecciona una canción local de la lista", "error");
        }
    });

    elements.btnRunShazamRecognition.addEventListener("click", async () => {
        const filePath = elements.tagFilePath.value;
        if (!filePath) {
            showToast("Selecciona o sube un archivo MP3 primero para escanear", "error");
            return;
        }

        elements.shazamStatusBadge.textContent = "Escaneando huella Shazam...";
        elements.shazamStatusBadge.className = "badge shazam";
        showToast("Escaneando audio con Shazam...", "info");

        try {
            const formData = new FormData();
            formData.append("file_path", filePath);
            
            const res = await fetch("/api/shazam-file", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            
            if (data.filepath) {
                elements.tagFilePath.value = data.filepath;
            }

            if (data.success && data.matched) {
                elements.tagTitle.value = data.title || "";
                elements.tagArtist.value = data.artist || "";
                elements.tagAlbum.value = data.album || "";
                elements.tagYear.value = data.year || "";
                elements.tagGenre.value = data.genre || "";
                elements.tagLyrics.value = data.lyrics || "";
                if (data.cover_url) {
                    elements.tagCoverUrl.value = data.cover_url;
                    elements.editorCoverPreview.src = data.cover_url;
                }
                elements.shazamStatusBadge.textContent = "Reconocido con Shazam ✓";
                elements.shazamStatusBadge.className = "badge shazam";
                showToast("¡Metadatos actualizados desde Shazam!", "success");
            } else {
                elements.shazamStatusBadge.textContent = "No encontrado en Shazam";
                elements.shazamStatusBadge.className = "badge";
                showToast(data.message || "No se hallaron coincidencias en Shazam", "error");
            }
        } catch (err) {
            showToast("Error en reconocimiento Shazam", "error");
        }
    });

    async function uploadAndRecognizeFile(file) {
        showToast("Subiendo y guardando archivo MP3...", "info");
        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/shazam-file", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (data.filepath) {
                elements.tagFilePath.value = data.filepath;
                state.currentEditingFile = data.filepath;
                elements.editorCoverPreview.src = `/api/cover-file?path=${encodeURIComponent(data.filepath)}&t=${Date.now()}`;
            }

            if (data.success && data.matched) {
                elements.tagTitle.value = data.title || "";
                elements.tagArtist.value = data.artist || "";
                elements.tagAlbum.value = data.album || "";
                elements.tagYear.value = data.year || "";
                elements.tagGenre.value = data.genre || "";
                elements.tagLyrics.value = data.lyrics || "";
                if (data.cover_url) {
                    elements.tagCoverUrl.value = data.cover_url;
                    elements.editorCoverPreview.src = data.cover_url;
                }
                elements.shazamStatusBadge.textContent = "Reconocido con Shazam ✓";
                elements.shazamStatusBadge.className = "badge shazam";
                showToast("¡Archivo guardado en tu carpeta e información hallada en Shazam!", "success");
            } else if (data.filepath) {
                elements.tagTitle.value = file.name.replace(".mp3", "");
                elements.shazamStatusBadge.textContent = "Metadatos manuales";
                elements.shazamStatusBadge.className = "badge";
                showToast("Archivo guardado en tu carpeta. Edita sus etiquetas libremente.", "info");
            } else {
                showToast(`Error: ${data.error}`, "error");
            }
            loadFilesList();
        } catch (err) {
            showToast("Error procesando archivo subido", "error");
        }
    }

    async function loadTagsIntoEditor(filePath) {
        state.currentEditingFile = filePath;
        elements.tagFilePath.value = filePath;
        elements.shazamStatusBadge.textContent = "Cargando etiquetas...";

        // Set cover preview to embedded cover art endpoint with cache-buster timestamp
        elements.editorCoverPreview.src = `/api/cover-file?path=${encodeURIComponent(filePath)}&t=${Date.now()}`;

        try {
            const res = await fetch("/api/read-tags", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ file_path: filePath })
            });
            const data = await res.json();

            if (data.success) {
                elements.tagTitle.value = data.title || "";
                elements.tagArtist.value = data.artist || "";
                elements.tagAlbum.value = data.album || "";
                elements.tagYear.value = data.year || "";
                elements.tagGenre.value = data.genre || "";
                elements.tagLyrics.value = data.lyrics || "";
                elements.shazamStatusBadge.textContent = "Etiquetas cargadas";
                elements.shazamStatusBadge.className = "badge";
            }
        } catch (err) {
            showToast("Error leyendo etiquetas del archivo", "error");
        }
    }

    function switchToEditorAndLoad(filePath) {
        document.querySelector('.nav-btn[data-tab="shazam-tab"]').click();
        loadTagsIntoEditor(filePath);
    }

    // Save Tags Form Submit
    elements.tagEditorForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const filePath = elements.tagFilePath.value;
        if (!filePath) {
            showToast("Ninguna canción seleccionada para guardar", "error");
            return;
        }

        const formData = new FormData();
        formData.append("file_path", filePath);
        formData.append("title", elements.tagTitle.value);
        formData.append("artist", elements.tagArtist.value);
        formData.append("album", elements.tagAlbum.value);
        formData.append("year", elements.tagYear.value);
        formData.append("genre", elements.tagGenre.value);
        formData.append("lyrics", elements.tagLyrics.value);
        formData.append("cover_url", elements.tagCoverUrl.value);

        if (elements.coverFileInput.files.length > 0) {
            formData.append("cover_file", elements.coverFileInput.files[0]);
        }

        try {
            const res = await fetch("/api/save-tags", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                const finalPath = data.filepath || filePath;
                elements.tagFilePath.value = finalPath;
                elements.coverFileInput.value = ""; // Reset file picker
                elements.editorCoverPreview.src = `/api/cover-file?path=${encodeURIComponent(finalPath)}&t=${Date.now()}`;
                showToast("¡Etiquetas ID3 y portada de álbum guardadas correctamente!", "success");
                loadFilesList();
            } else {
                showToast(`Error al guardar: ${data.error}`, "error");
            }
        } catch (err) {
            showToast("Error guardando metadatos", "error");
        }
    });

    // Cover File Upload Preview
    elements.coverFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            const reader = new FileReader();
            reader.onload = (evt) => {
                elements.editorCoverPreview.src = evt.target.result;
                elements.tagCoverUrl.value = evt.target.result; // data URI
            };
            reader.readAsDataURL(e.target.files[0]);
        }
    });

    // --- Files Tab ---
    elements.btnRefreshFiles.addEventListener("click", loadFilesList);
    elements.btnOpenDirExplorer.addEventListener("click", () => openFolder(state.currentDir));
    elements.filesSearchInput.addEventListener("input", filterFilesTable);

    async function loadFilesList() {
        try {
            const res = await fetch(`/api/files?directory=${encodeURIComponent(state.currentDir)}`);
            const data = await res.json();
            state.localFiles = data.files || [];

            renderFilesTable(state.localFiles);
            populateLocalFilesSelect(state.localFiles);
        } catch (err) {
            showToast("Error cargando lista de archivos locales", "error");
        }
    }

    function renderFilesTable(files) {
        if (files.length === 0) {
            elements.filesTableBody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center">No se encontraron archivos MP3 en esta carpeta.</td>
                </tr>
            `;
            return;
        }

        elements.filesTableBody.innerHTML = "";
        files.forEach(f => {
            const row = document.createElement("tr");
            const coverSrc = `/api/cover-file?path=${encodeURIComponent(f.filepath)}&t=${Date.now()}`;
            row.innerHTML = `
                <td>
                    <div style="display:flex; align-items:center; gap:0.75rem;">
                        <img src="${coverSrc}" style="width:36px; height:36px; border-radius:6px; object-fit:cover;" onerror="this.onerror=null; this.src='/static/images/default_cover.svg';">
                        <strong>${f.filename}</strong>
                    </div>
                </td>
                <td>${f.size_mb} MB</td>
                <td>${new Date(f.modified * 1000).toLocaleDateString()}</td>
                <td class="text-right">
                    <button class="btn-action btn-sm play-file-btn" data-path="${f.filepath}" data-name="${f.filename}">
                        <i class="fa-solid fa-play"></i> Reproducir
                    </button>
                    <button class="btn-action btn-sm edit-file-btn" data-path="${f.filepath}">
                        <i class="fa-solid fa-pen"></i> Editar
                    </button>
                </td>
            `;
            elements.filesTableBody.appendChild(row);
        });

        // Add event listeners to table buttons
        document.querySelectorAll(".play-file-btn").forEach(b => {
            b.onclick = () => {
                const path = b.getAttribute("data-path");
                const name = b.getAttribute("data-name");
                const cover = `/api/cover-file?path=${encodeURIComponent(path)}&t=${Date.now()}`;
                playAudio(path, name, "Guardado Local", cover);
            };
        });

        document.querySelectorAll(".edit-file-btn").forEach(b => {
            b.onclick = () => {
                const path = b.getAttribute("data-path");
                switchToEditorAndLoad(path);
            };
        });
    }

    function populateLocalFilesSelect(files) {
        elements.localFilesSelect.innerHTML = '<option value="">-- Selecciona una canción guardada --</option>';
        files.forEach(f => {
            const opt = document.createElement("option");
            opt.value = f.filepath;
            opt.textContent = `${f.filename} (${f.size_mb} MB)`;
            elements.localFilesSelect.appendChild(opt);
        });
    }

    function filterFilesTable() {
        const query = elements.filesSearchInput.value.toLowerCase().trim();
        const filtered = state.localFiles.filter(f => f.filename.toLowerCase().includes(query));
        renderFilesTable(filtered);
    }

    // --- Settings Tab Submit ---
    elements.settingsForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const newDir = elements.settingsDirInput.value.trim();
        if (newDir) {
            updateCurrentDirectory(newDir);
        }
    });

    // --- Audio Player ---
    function playAudio(filePath, title, artist, coverUrl) {
        elements.stickyPlayer.classList.remove("hidden");
        elements.playerTitle.textContent = title || "Canción";
        elements.playerArtist.textContent = artist || "Artista";
        elements.playerCover.src = coverUrl || `/api/cover-file?path=${encodeURIComponent(filePath)}&t=${Date.now()}`;

        const streamUrl = `/api/audio-file?path=${encodeURIComponent(filePath)}`;
        elements.mainAudioElement.src = streamUrl;
        elements.mainAudioElement.play();
    }

    elements.playerCloseBtn.addEventListener("click", () => {
        elements.mainAudioElement.pause();
        elements.stickyPlayer.classList.add("hidden");
    });

    // --- Open Folder Helper ---
    async function openFolder(path) {
        try {
            await fetch("/api/open-folder", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: path })
            });
            showToast("Carpeta abierta en el explorador", "info");
        } catch (err) {
            showToast("No se pudo abrir la carpeta automáticamente", "error");
        }
    }

    // --- Toast Notifications ---
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let icon = "fa-circle-info";
        if (type === "success") icon = "fa-circle-check";
        if (type === "error") icon = "fa-triangle-exclamation";

        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        elements.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(50px)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
});
