const TRACKING_SWATCHES = [
  "#16a085", "#27ae60", "#2980b9", "#8e44ad",
  "#2c3e50", "#f39c12", "#d35400", "#c0392b", "#7f8c8d"
];

// Detect if we are in Read-Only Mode via ?readonly=true query parameter
const urlParams = new URLSearchParams(window.location.search);
const isReadOnly = urlParams.get('readonly') === 'true';

if (isReadOnly) {
  document.body.classList.add('readonly-mode');
}

let boardTitle = "Document board";
let categories = [];
let columns = [];
let cards = [];
let notes = [];
let boardVersion = 1;
let draftColumns = [];
let draftCategories = [];
let activeEditCardId = null;
let activeEditCategoryId = null;
let activeEditNoteId = null;
let kbDraggingCard = null;
let currentView = 'column'; // 'column' or 'table'

let isStretched = localStorage.getItem('boardStretched') === 'true';
let isLight = localStorage.getItem('boardLightTheme') === 'true';
applyThemeUI();
applyStretchUI();

function toggleTheme() { isLight = !isLight; localStorage.setItem('boardLightTheme', isLight); applyThemeUI(); }
function applyThemeUI() { document.body.classList.toggle('light-theme', isLight); }
function toggleStretch() { isStretched = !isStretched; localStorage.setItem('boardStretched', isStretched); applyStretchUI(); render(); }
function applyStretchUI() {
    const wrap = document.querySelector('.board-wrapper');
    const main = document.getElementById('main-container');
    if(wrap) wrap.classList.toggle('stretched', isStretched);
    if(main) main.classList.toggle('stretched-mode', isStretched);
}

function toggleView() {
  currentView = (currentView === 'column') ? 'table' : 'column';
  const btn = document.getElementById('view-toggle-btn');
  if (btn) {
    btn.textContent = (currentView === 'column') ? '☰ Table View' : '🎚️ Board View';
  }
  render();
}

// Modal Locking Logic
function openOverlay(id, focusTargetId) {
    if (isReadOnly && id !== 'help-overlay') return; // Read-only modes cannot open editing overlays
    document.getElementById(id).classList.add('open');
    document.body.classList.add('modal-open');
    if (focusTargetId) {
        setTimeout(() => document.getElementById(focusTargetId).focus(), 50);
    }
}
function closeOverlay(id) {
    document.getElementById(id).classList.remove('open');
    document.body.classList.remove('modal-open');
    activeEditCardId = null;
    activeEditCategoryId = null;
    activeEditNoteId = null;
}
function toggleHelp() {
    const el = document.getElementById('help-overlay');
    if(el.classList.contains('open')) closeOverlay('help-overlay');
    else openOverlay('help-overlay');
}

function triggerAddCard() {
    if (isReadOnly) return;
    const btn = document.querySelector('.add-card-btn');
    const row = document.querySelector('.add-row');
    const input = row ? row.querySelector('textarea') : null;
    if (row && row.classList.contains('open') && input) input.focus();
    else if (btn) btn.click();
}

function genId(prefix) { return prefix + '-' + Math.random().toString(36).substring(2, 10); }
function getFormattedDate() {
    const d = new Date(); const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

async function loadData() {
  const res = await fetch('/api/data');
  const data = await res.json();
  boardTitle = data.board_title;
  categories = data.categories || [];
  columns = data.columns;
  cards = data.cards;
  notes = data.notes || [];
  boardVersion = data.version || 1;
  document.getElementById('board-title').textContent = boardTitle;
  render();
  renderStickyNotes();
}

async function post(body) {
  if (isReadOnly) {
      console.warn("Write operation blocked locally: Read-Only Mode is active.");
      return false;
  }
  body.version = boardVersion;
  try {
      const res = await fetch('/api/data', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (res.status === 409) { alert((await res.json()).error); await loadData(); return false; }
      if (res.ok) { boardVersion = (await res.json()).new_version; return true; }
      return false;
  } catch (e) { return false; }
}

let noteDebounce;
function scheduleNoteSave() {
    if (isReadOnly) return;
    clearTimeout(noteDebounce);
    noteDebounce = setTimeout(async () => {
        await post({ action: 'update_notes', notes: notes });
    }, 500);
}

function renderStickyNotes() {
    const list = document.getElementById('sticky-notes-list');
    list.innerHTML = '';
    notes.forEach(note => {
        const wrapper = document.createElement('div'); wrapper.className = 'individual-note';

        if (!isReadOnly) {
            const actions = document.createElement('div'); actions.className = 'card-actions';
            actions.style.position = 'absolute'; actions.style.top = '8px'; actions.style.right = '8px';

            const editBtn = document.createElement('button'); editBtn.className = 'card-btn edit-btn'; editBtn.textContent = 'edit';
            editBtn.onclick = () => { openEditNote(note.id); };

            const delBtn = document.createElement('button'); delBtn.className = 'card-btn del-btn'; delBtn.textContent = 'del';
            delBtn.onclick = () => { notes = notes.filter(x => x.id !== note.id); renderStickyNotes(); scheduleNoteSave(); };

            actions.appendChild(editBtn); actions.appendChild(delBtn);
            wrapper.appendChild(actions);
        }

        const textDiv = document.createElement('div'); textDiv.className = 'individual-note-text';
        textDiv.textContent = note.text || "Empty Note";
        wrapper.appendChild(textDiv);

        list.appendChild(wrapper);
    });
}
function openEditNote(id) {
    if (isReadOnly) return;
    activeEditNoteId = id;
    const noteObj = notes.find(x => x.id === id);
    document.getElementById('edit-note-textarea').value = noteObj.text;
    openOverlay('note-edit-overlay', 'edit-note-textarea');
}
async function saveEditNote() {
    if (isReadOnly || !activeEditNoteId) return;
    const val = document.getElementById('edit-note-textarea').value.trim();
    const noteObj = notes.find(x => x.id === activeEditNoteId);
    if(noteObj) noteObj.text = val;
    closeOverlay('note-edit-overlay');
    renderStickyNotes();
    scheduleNoteSave();
}
document.getElementById('edit-note-textarea').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); saveEditNote(); }
});

function addStickyNote() {
    if (isReadOnly) return;
    const newId = genId('note');
    notes.push({ id: newId, text: '' });
    renderStickyNotes(); scheduleNoteSave();
    openEditNote(newId);
}

function render() {
  const board = document.getElementById('board'); board.innerHTML = '';

  if (currentView === 'table') {
    // Render clean, beautiful Data Table View
    board.className = 'board-table-container';

    const table = document.createElement('table');
    table.className = 'board-table';

    const thead = document.createElement('thead');
    thead.innerHTML = `
      <tr>
        <th>Task Details</th>
        <th>Column / Status</th>
        <th>Category</th>
        <th>Created At</th>
        ${!isReadOnly ? '<th>Actions</th>' : ''}
      </tr>
    `;
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    if (cards.length === 0) {
      const row = document.createElement('tr');
      row.innerHTML = `<td colspan="${!isReadOnly ? 5 : 4}" style="text-align: center; color: var(--meta-text); padding: 24px;">No tasks created yet. Click "+ Card" above to add some!</td>`;
      tbody.appendChild(row);
    } else {
      cards.forEach(c => {
        const col = columns.find(x => x.id === c.column_id);
        const cat = categories.find(x => x.id === c.category_id);

        const row = document.createElement('tr');

        // Task text with title and description lines
        const lines = c.text.split('\n');
        const titleText = lines[0];
        const descText = lines.length > 1 ? `<div style="font-size: 12px; opacity: 0.8; margin-top: 4px;">${lines.slice(1).join('<br>')}</div>` : '';

        const statusBadge = col ? `<span class="status-badge" style="background-color: ${col.color}">${col.label}</span>` : '';
        const catPill = cat ? `<span class="cat-pill" style="background-color: ${cat.color}">${cat.label}</span>` : '';
        const timeStr = c.created_at ? c.created_at.substring(0, 16) : '';

        let actionsTd = '';
        if (!isReadOnly) {
          actionsTd = `
            <td>
              <button class="card-btn edit-btn" style="margin-right: 4px;">Edit</button>
              <button class="card-btn del-btn">Delete</button>
            </td>
          `;
        }

        row.innerHTML = `
          <td><div style="font-weight: 600;">${titleText}</div>${descText}</td>
          <td>${statusBadge}</td>
          <td>${catPill}</td>
          <td>${timeStr}</td>
          ${actionsTd}
        `;

        // Wire actions
        if (!isReadOnly) {
          const editB = row.querySelector('.edit-btn');
          const delB = row.querySelector('.del-btn');
          if (editB) editB.onclick = () => openEditCard(c.id);
          if (delB) {
            delB.onclick = async () => {
              cards = cards.filter(x => x.id !== c.id);
              const ok = await post({ action: 'delete', card: c.text, column_id: c.column_id, card_id: c.id });
              if (ok) render();
            };
          }
        }

        tbody.appendChild(row);
      });
    }
    table.appendChild(tbody);
    board.appendChild(table);
    return;
  }

  // Classic Column View
  board.className = 'board-wrapper' + (isStretched ? ' stretched' : '');

  columns.forEach(colData => {
    const col = document.createElement('div'); col.className = 'board-col'; col.dataset.colId = colData.id;
    const head = document.createElement('div'); head.className = 'col-head'; head.style.backgroundColor = colData.color; head.textContent = colData.label;
    col.appendChild(head);

    const zone = document.createElement('div'); zone.className = 'drop-zone'; zone.dataset.colId = colData.id;

    if (colData.is_intake && !isReadOnly) {
        const addContainer = document.createElement('div'); addContainer.className = 'add-container';
        const addBtn = document.createElement('button'); addBtn.className = 'add-card-btn'; addBtn.textContent = '+ Add card (N)';
        const addRow = document.createElement('div'); addRow.className = 'add-row';
        const pillHeader = document.createElement('div'); pillHeader.style.fontSize = '11px'; pillHeader.style.color = '#7f8c8d'; pillHeader.style.marginBottom = '6px'; pillHeader.textContent = 'Category (Alt + \u2190/\u2192)';

        const pillSelector = document.createElement('div'); pillSelector.className = 'pill-selector';
        let selectedPillId = categories.length > 0 ? categories[0].id : null;

        const renderPills = () => {
            pillSelector.innerHTML = '';
            categories.forEach(cat => {
                const p = document.createElement('div'); p.className = 'pill-option' + (selectedPillId === cat.id ? ' selected' : '');
                p.style.backgroundColor = cat.color; p.textContent = cat.label;
                p.onclick = () => { selectedPillId = cat.id; renderPills(); }; pillSelector.appendChild(p);
            });
        }; renderPills();

        const cycleAddPills = (dir) => {
            if (categories.length === 0) return;
            let idx = categories.findIndex(c => c.id === selectedPillId);
            idx = (idx === -1) ? 0 : (idx + dir + categories.length) % categories.length;
            selectedPillId = categories[idx].id; renderPills();
        };

        const input = document.createElement('textarea'); input.placeholder = 'Task title...\n(Shift+Enter for desc)';
        const btnGroup = document.createElement('div'); btnGroup.className = 'btn-group';
        const goBtn = document.createElement('button'); goBtn.textContent = 'Add';
        const cancelBtn = document.createElement('button'); cancelBtn.textContent = 'Cancel'; cancelBtn.className = 'btn-cancel';

        const closeAdd = () => { addRow.classList.remove('open'); addBtn.style.display = 'block'; input.value = ''; };
        const doAdd = async () => {
          const val = input.value.trim(); if (!val) { closeAdd(); return; }
          const id = genId('card'); const ts = getFormattedDate();
          cards.push({ id, text: val, column_id: colData.id, category_id: selectedPillId, created_at: ts }); closeAdd();
          const ok = await post({ action: 'create', card: val, column_id: colData.id, category_id: selectedPillId, created_at: ts }); if (ok) render();
        };

        goBtn.onclick = doAdd; cancelBtn.onclick = closeAdd;
        input.addEventListener('keydown', e => {
            if (e.altKey && e.key === 'ArrowLeft') { e.preventDefault(); cycleAddPills(-1); }
            else if (e.altKey && e.key === 'ArrowRight') { e.preventDefault(); cycleAddPills(1); }
            else if (e.key === 'Escape') closeAdd();
            else if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doAdd(); }
        });
        addBtn.onclick = () => { addBtn.style.display = 'none'; addRow.classList.add('open'); input.focus(); };
        btnGroup.appendChild(cancelBtn); btnGroup.appendChild(goBtn);
        addRow.appendChild(pillHeader); addRow.appendChild(pillSelector); addRow.appendChild(input); addRow.appendChild(btnGroup);
        addContainer.appendChild(addBtn); addContainer.appendChild(addRow); col.appendChild(addContainer);
    }
    setupDropZone(zone, colData.id); renderCardsInto(zone, colData); col.appendChild(zone); board.appendChild(col);
  });
}

function renderCardsInto(container, columnData) {
  const targetCards = cards.filter(c => c.column_id === columnData.id);
  targetCards.forEach(c => {
    const cardEl = document.createElement('div'); cardEl.className = 'card'; cardEl.draggable = !isReadOnly; cardEl.dataset.id = c.id; cardEl.tabIndex = 0;
    const cat = categories.find(x => x.id === c.category_id); cardEl.style.background = cat ? cat.color : 'var(--bg-col)';
    if (cat) { const badge = document.createElement('div'); badge.className = 'pill-badge'; badge.textContent = cat.label; cardEl.appendChild(badge); }
    const lines = c.text.split('\n');
    const titleEl = document.createElement('div'); titleEl.style.fontWeight = 'bold'; titleEl.textContent = lines[0]; cardEl.appendChild(titleEl);
    if (lines.length > 1) { const descEl = document.createElement('div'); descEl.style.fontSize = '12px'; descEl.style.marginTop = '6px'; descEl.style.opacity = '0.9'; descEl.textContent = lines.slice(1).join('\n'); cardEl.appendChild(descEl); }
    const footerEl = document.createElement('div'); footerEl.className = 'card-footer';
    const timeEl = document.createElement('span'); timeEl.textContent = c.created_at ? c.created_at.substring(0, 16) : ''; footerEl.appendChild(timeEl);

    if (!isReadOnly) {
        const actionsEl = document.createElement('div'); actionsEl.className = 'card-actions';
        const editBtn = document.createElement('button'); editBtn.className = 'card-btn edit-btn'; editBtn.textContent = 'edit'; editBtn.onclick = (e) => { e.stopPropagation(); openEditCard(c.id); };
        const del = document.createElement('button'); del.className = 'card-btn del-btn'; del.textContent = 'del';
        del.onclick = async (e) => { e.stopPropagation(); cards = cards.filter(x => x.id !== c.id); const ok = await post({ action: 'delete', card: c.text, column_id: columnData.id, card_id: c.id }); if (ok) render(); };
        actionsEl.appendChild(editBtn); actionsEl.appendChild(del); footerEl.appendChild(actionsEl);
    }

    cardEl.appendChild(footerEl);
    cardEl.addEventListener('dragstart', e => { if (isReadOnly || kbDraggingCard) return e.preventDefault(); cardEl.classList.add('dragging'); e.dataTransfer.setData('text/plain', c.id); });
    cardEl.addEventListener('dragend', () => cardEl.classList.remove('dragging'));
    container.appendChild(cardEl);
  });
}

// Global Keyboard Router
document.addEventListener('keydown', async (e) => {
    const isInput = ['TEXTAREA', 'INPUT'].includes(document.activeElement.tagName);
    const hasOverlayOpen = document.body.classList.contains('modal-open');

    if (e.key === 'Escape') {
        if(hasOverlayOpen) {
            document.querySelectorAll('.overlay.open').forEach(el => el.classList.remove('open'));
            document.body.classList.remove('modal-open');
            activeEditCardId = null;
            activeEditCategoryId = null;
            activeEditNoteId = null;
        }
        return;
    }

    if (isInput) return; // Ignore hotkeys when typing

    const key = e.key.toLowerCase();

    // Global Menu Toggles
    if (!hasOverlayOpen && !kbDraggingCard) {
        if (key === '?') { e.preventDefault(); toggleHelp(); return; }
        if (key === 'n') { e.preventDefault(); triggerAddCard(); return; }
        if (key === 'm') { e.preventDefault(); addStickyNote(); return; }
        if (key === 's') { e.preventDefault(); toggleStretch(); return; }
        if (key === 't') { e.preventDefault(); toggleTheme(); return; }
        if (key === 'c') { e.preventDefault(); openConfig(); return; }

        if (e.shiftKey && key === 'b') { e.preventDefault(); saveBackup(); return; }
        if (e.shiftKey && key === 'r') { e.preventDefault(); document.getElementById('restore-file').click(); return; }
        if (e.shiftKey && key === 'e') { e.preventDefault(); exportLog(); return; }
    }

    // Card Focus & Drag Navigation Engine
    if (hasOverlayOpen || currentView === 'table') return; // Disable keyboard focus layout movement in table mode

    const active = document.activeElement;
    const isCard = active.classList.contains('card');
    const isDirKey = ['arrowup','arrowdown','arrowleft','arrowright','h','j','k','l'].includes(key);

    if (!kbDraggingCard && isDirKey) {
        e.preventDefault();
        const allCards = Array.from(document.querySelectorAll('.card'));
        if (allCards.length === 0) return;

        if (!isCard) { allCards[0].focus(); return; }

        if (['j', 'arrowdown'].includes(key)) {
            const next = active.nextElementSibling;
            if (next && next.classList.contains('card')) next.focus();
        } else if (['k', 'arrowup'].includes(key)) {
            const prev = active.previousElementSibling;
            if (prev && prev.classList.contains('card')) prev.focus();
        } else if (['l', 'arrowright'].includes(key)) {
            const cols = Array.from(document.querySelectorAll('.board-col'));
            let idx = cols.indexOf(active.closest('.board-col'));
            while(idx < cols.length - 1) {
                idx++;
                const c = cols[idx].querySelector('.card');
                if(c) { c.focus(); break; }
            }
        } else if (['h', 'arrowleft'].includes(key)) {
            const cols = Array.from(document.querySelectorAll('.board-col'));
            let idx = cols.indexOf(active.closest('.board-col'));
            while(idx > 0) {
                idx--;
                const c = cols[idx].querySelector('.card');
                if(c) { c.focus(); break; }
            }
        }
        return;
    }

    if (isCard && !kbDraggingCard) {
        if (key === 'e') { e.preventDefault(); if (!isReadOnly) active.querySelector('.edit-btn').click(); }
        if (key === 'delete' || key === 'backspace') { e.preventDefault(); if (!isReadOnly) active.querySelector('.del-btn').click(); }
        if (key === ' ' || key === 'spacebar') { e.preventDefault(); if (!isReadOnly) { kbDraggingCard = active; active.classList.add('keyboard-dragging'); } }
    } else if (kbDraggingCard) {
        e.preventDefault();
        if (key === 'enter' || key === ' ' || key === 'spacebar') {
            kbDraggingCard.classList.remove('keyboard-dragging');
            const newColId = kbDraggingCard.closest('.board-col').dataset.colId;
            const cardId = kbDraggingCard.dataset.id;

            const domCards = document.querySelectorAll('.card');
            const newCardsArray = [];
            domCards.forEach(el => {
                const cObj = cards.find(x => x.id === el.dataset.id);
                if (cObj) { if (cObj.id === cardId) cObj.column_id = newColId; newCardsArray.push(cObj); }
            }); cards = newCardsArray;
            await post({ action: 'update_cards', cards: cards }); render();
            setTimeout(() => { const el = document.querySelector(`[data-id='${cardId}']`); if(el) el.focus(); }, 50);
            kbDraggingCard = null; return;
        }
        const currentZone = kbDraggingCard.closest('.drop-zone');
        const currentCol = kbDraggingCard.closest('.board-col');

        if (['arrowleft', 'h'].includes(key)) {
            const prevCol = currentCol.previousElementSibling;
            if (prevCol) { prevCol.querySelector('.drop-zone').appendChild(kbDraggingCard); kbDraggingCard.focus(); }
        } else if (['arrowright', 'l'].includes(key)) {
            const nextCol = currentCol.nextElementSibling;
            if (nextCol) { nextCol.querySelector('.drop-zone').appendChild(kbDraggingCard); kbDraggingCard.focus(); }
        } else if (['arrowup', 'k'].includes(key)) {
            const prevCard = kbDraggingCard.previousElementSibling;
            if (prevCard && prevCard.classList.contains('card')) { currentZone.insertBefore(kbDraggingCard, prevCard); kbDraggingCard.focus(); }
        } else if (['arrowdown', 'j'].includes(key)) {
            const nextCard = kbDraggingCard.nextElementSibling;
            if (nextCard && nextCard.classList.contains('card')) { currentZone.insertBefore(kbDraggingCard, nextCard.nextElementSibling); kbDraggingCard.focus(); }
        }
    }
});

function renderEditPills() {
    const container = document.getElementById('edit-pill-selector');
    container.innerHTML = '<div style="font-size:11px; color:#7f8c8d; margin-bottom:6px;">Category (Alt + \u2190/\u2192)</div>';
    const wrap = document.createElement('div'); wrap.className = 'pill-selector';
    categories.forEach(cat => {
        const p = document.createElement('div'); p.className = 'pill-option' + (activeEditCategoryId === cat.id ? ' selected' : '');
        p.style.backgroundColor = cat.color; p.textContent = cat.label;
        p.onclick = () => { activeEditCategoryId = cat.id; renderEditPills(); }; wrap.appendChild(p);
    }); container.appendChild(wrap);
}
function cycleEditPills(dir) {
    if (categories.length === 0) return;
    let idx = categories.findIndex(c => c.id === activeEditCategoryId);
    idx = (idx === -1) ? 0 : (idx + dir + categories.length) % categories.length;
    activeEditCategoryId = categories[idx].id; renderEditPills();
}
document.getElementById('edit-card-textarea').addEventListener('keydown', e => {
    if (e.altKey && e.key === 'ArrowLeft') { e.preventDefault(); cycleEditPills(-1); }
    else if (e.altKey && e.key === 'ArrowRight') { e.preventDefault(); cycleEditPills(1); }
    else if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); saveEditCard(); }
});

function openEditCard(id) {
    if (isReadOnly) return;
    activeEditCardId = id; const cardObj = cards.find(x => x.id === id); activeEditCategoryId = cardObj.category_id;
    renderEditPills(); document.getElementById('edit-card-textarea').value = cardObj.text;
    openOverlay('card-edit-overlay', 'edit-card-textarea');
}
async function saveEditCard() {
    if (isReadOnly || !activeEditCardId) return; const val = document.getElementById('edit-card-textarea').value.trim();
    if(val) { const cardObj = cards.find(x => x.id === activeEditCardId); cardObj.text = val; cardObj.category_id = activeEditCategoryId; }
    closeOverlay('card-edit-overlay'); await post({ action: 'update_cards', cards: cards }); render();
}

function getDragAfterElement(container, y) {
  const draggables = [...container.querySelectorAll('.card:not(.dragging)')];
  return draggables.reduce((closest, child) => {
    const box = child.getBoundingClientRect(); const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) return { offset: offset, element: child }; return closest;
  }, { offset: Number.NEGATIVE_INFINITY }).element;
}
function clearDropIndicators() { document.querySelectorAll('.card').forEach(c => c.classList.remove('drag-target')); }

function setupDropZone(zone, columnId) {
  if (isReadOnly) return;
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); clearDropIndicators(); const after = getDragAfterElement(zone, e.clientY); if (after) after.classList.add('drag-target'); });
  zone.addEventListener('dragleave', () => { zone.classList.remove('dragover'); clearDropIndicators(); });
  zone.addEventListener('drop', async e => {
    e.preventDefault(); zone.classList.remove('dragover'); clearDropIndicators();
    const id = e.dataTransfer.getData('text/plain'); if (!id) return;
    const after = getDragAfterElement(zone, e.clientY); const obj = cards.find(x => x.id === id); if (!obj) return;
    obj.column_id = columnId; const draggedEl = document.querySelector(`[data-id='${id}']`);
    if (draggedEl) { if (after == null) zone.appendChild(draggedEl); else zone.insertBefore(draggedEl, after); }
    const domCards = document.querySelectorAll('.card'); const newCardsArray = [];
    domCards.forEach(el => { const cObj = cards.find(x => x.id === el.dataset.id); if (cObj) newCardsArray.push(cObj); });
    cards.forEach(c => { if (!newCardsArray.includes(c)) newCardsArray.push(c); }); cards = newCardsArray;
    await post({ action: 'update_cards', cards: cards }); render();
  });
}

function exportLog() { window.location.href = '/api/export'; }
function saveBackup() { window.location.href = '/api/backup'; }
async function loadBackup(event) {
  if (isReadOnly) return;
  const file = event.target.files[0]; if (!file) return;
  const text = await file.text();
  try {
    const res = await fetch('/api/restore', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: text });
    if(res.ok) { await loadData(); alert('Backup recovered.'); } else alert('Rejected.');
  } catch (err) { alert('Invalid file.'); } event.target.value = '';
}

function openConfig() {
  if (isReadOnly) return;
  draftColumns = JSON.parse(JSON.stringify(columns.filter(c => !c.is_intake))); draftCategories = JSON.parse(JSON.stringify(categories));
  document.getElementById('cfg-title').value = boardTitle; renderConfigLists();
  openOverlay('overlay', 'cfg-title');
}

function renderConfigLists() {
  const catWrap = document.getElementById('cfg-cat-list'); const trackWrap = document.getElementById('cfg-track-cols');
  catWrap.innerHTML = ''; trackWrap.innerHTML = '';
  draftCategories.forEach((cat, idx) => {
    const row = document.createElement('div'); row.className = 'config-row';
    const input = document.createElement('input'); input.type = 'text'; input.value = cat.label; input.oninput = () => { draftCategories[idx].label = input.value; };
    const swatchRow = document.createElement('div'); swatchRow.className = 'swatch-row';
    TRACKING_SWATCHES.forEach(color => {
      const sw = document.createElement('div'); sw.className = 'swatch' + (cat.color === color ? ' selected' : '');
      sw.style.background = color; sw.onclick = () => { draftCategories[idx].color = color; renderConfigLists(); }; swatchRow.appendChild(sw);
    });
    const del = document.createElement('button'); del.className = 'config-del'; del.innerHTML = '&times;'; del.title = "Delete";
    del.onclick = () => { draftCategories.splice(idx, 1); renderConfigLists(); };
    row.appendChild(input); row.appendChild(swatchRow); row.appendChild(del); catWrap.appendChild(row);
  });

  draftColumns.forEach((col, idx) => {
    const row = document.createElement('div'); row.className = 'config-row';
    const input = document.createElement('input'); input.type = 'text'; input.value = col.label; input.oninput = () => { draftColumns[idx].label = input.value; };
    const swatchRow = document.createElement('div'); swatchRow.className = 'swatch-row';
    TRACKING_SWATCHES.forEach(color => {
      const sw = document.createElement('div'); sw.className = 'swatch' + (col.color === color ? ' selected' : '');
      sw.style.background = color; sw.onclick = () => { draftColumns[idx].color = color; renderConfigLists(); }; swatchRow.appendChild(sw);
    });
    const actionBlock = document.createElement('div'); actionBlock.style.display = 'flex'; actionBlock.style.gap = '2px';
    const upBtn = document.createElement('button'); upBtn.className = 'config-del'; upBtn.innerHTML = '&#8593;'; upBtn.title = "Move Up";
    upBtn.onclick = () => { if(idx > 0) { const t = draftColumns[idx]; draftColumns[idx] = draftColumns[idx-1]; draftColumns[idx-1] = t; renderConfigLists(); } };
    const dnBtn = document.createElement('button'); dnBtn.className = 'config-del'; dnBtn.innerHTML = '&#8595;'; dnBtn.title = "Move Down";
    dnBtn.onclick = () => { if(idx < draftColumns.length-1) { const t = draftColumns[idx]; draftColumns[idx] = draftColumns[idx+1]; draftColumns[idx+1] = t; renderConfigLists(); } };
    const del = document.createElement('button'); del.className = 'config-del'; del.innerHTML = '&times;'; del.title = "Delete";
    del.onclick = () => { draftColumns.splice(idx, 1); renderConfigLists(); };
    actionBlock.appendChild(upBtn); actionBlock.appendChild(dnBtn); actionBlock.appendChild(del);
    row.appendChild(input); row.appendChild(swatchRow); row.appendChild(actionBlock); trackWrap.appendChild(row);
  });
}
function addCategoryDraft() {
  const input = document.getElementById('cfg-new-cat'); const val = input.value.trim(); if (!val) return;
  draftCategories.push({ id: genId('cat'), label: val, color: TRACKING_SWATCHES[draftCategories.length % TRACKING_SWATCHES.length] }); input.value = ''; renderConfigLists();
}
function addColumnDraft() {
  const input = document.getElementById('cfg-new-track'); const val = input.value.trim(); if (!val) return;
  draftColumns.push({ id: genId('col'), label: val, color: TRACKING_SWATCHES[draftColumns.length % TRACKING_SWATCHES.length], is_intake: false }); input.value = ''; renderConfigLists();
}
async function saveConfig() {
  if (isReadOnly) return;
  const title = document.getElementById('cfg-title').value.trim() || 'Document board';
  const ok = await post({ action: 'configure', board_title: title, columns: [columns.find(c => c.is_intake), ...draftColumns], categories: draftCategories });
  if (ok) { closeOverlay('overlay'); await loadData(); }
}
loadData();
