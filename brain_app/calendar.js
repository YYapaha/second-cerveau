// brain_app/calendar.js — Module calendrier Electron
'use strict';

const API = 'http://127.0.0.1:7842';

const ICONS = { rdv: '📅', anniversaire: '🎂', tache: '✅', deadline: '⏰' };
const JOURS = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];
const MOIS  = ['Janvier','Février','Mars','Avril','Mai','Juin',
               'Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

let _currentYear  = new Date().getFullYear();
let _currentMonth = new Date().getMonth(); // 0-based
let _events       = [];
let _activeFilter = 'all';

// ── API ──────────────────────────────────────────────────────────────────────

async function fetchEvents() {
  try {
    const r = await fetch(`${API}/calendar/events`);
    _events = await r.json();
  } catch (e) {
    console.error('Erreur fetch events:', e);
    _events = [];
  }
}

async function createEvent(payload) {
  const r = await fetch(`${API}/calendar/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function updateEvent(id, payload) {
  const r = await fetch(`${API}/calendar/events/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function deleteEvent(id) {
  const r = await fetch(`${API}/calendar/events/${id}`, { method: 'DELETE' });
  if (!r.ok) throw new Error(await r.text());
}

async function addReminder(eventId, reminder) {
  const r = await fetch(`${API}/calendar/events/${eventId}/reminders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(reminder),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function deleteReminder(eventId, reminderId) {
  await fetch(`${API}/calendar/events/${eventId}/reminders/${reminderId}`, {
    method: 'DELETE',
  });
}

// ── Mini-grille ──────────────────────────────────────────────────────────────

function renderMiniGrid() {
  const grid  = document.getElementById('cal-mini-grid');
  const label = document.getElementById('cal-month-label');
  if (!grid || !label) return;

  label.textContent = `${MOIS[_currentMonth]} ${_currentYear}`;

  const today     = new Date();
  const firstDay  = new Date(_currentYear, _currentMonth, 1);
  const daysInMonth = new Date(_currentYear, _currentMonth + 1, 0).getDate();

  // Jour de semaine du 1er (0=dim → transformer en 0=lun)
  let startDow = firstDay.getDay(); // 0=dim
  startDow = (startDow + 6) % 7;   // 0=lun

  // Jours du mois avec event
  const eventDays = new Set(
    _events
      .filter(e => {
        const d = new Date(e.date_debut);
        return d.getFullYear() === _currentYear && d.getMonth() === _currentMonth;
      })
      .map(e => new Date(e.date_debut).getDate())
  );

  grid.innerHTML = JOURS.map(j => `<div class="cal-day-label">${j}</div>`).join('');

  // Cellules vides avant le 1er
  for (let i = 0; i < startDow; i++) {
    grid.innerHTML += '<div class="cal-day"></div>';
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const isToday =
      d === today.getDate() &&
      _currentMonth === today.getMonth() &&
      _currentYear  === today.getFullYear();
    const hasEvent = eventDays.has(d);
    grid.innerHTML += `<div class="cal-day${isToday ? ' today' : ''}${hasEvent ? ' has-event' : ''}">${d}</div>`;
  }
}

// ── Agenda ───────────────────────────────────────────────────────────────────

function formatDateLabel(dateStr) {
  const d    = new Date(dateStr);
  const now  = new Date();
  const diff = Math.round((d.setHours(0,0,0,0) - now.setHours(0,0,0,0)) / 86400000);
  const dd   = d.getDate().toString().padStart(2,'0');
  const mm   = (d.getMonth()+1).toString().padStart(2,'0');
  const base = `${dd}/${mm}`;
  if (diff === 0) return { label: `Aujourd'hui · ${base}`, today: true };
  if (diff === 1) return { label: `Demain · ${base}`, today: false };
  if (diff > 0)   return { label: `Dans ${diff} jours · ${base}`, today: false };
  return { label: base, today: false };
}

function formatEventTime(dateStr) {
  if (!dateStr.includes('T')) return 'Toute la journée';
  const d = new Date(dateStr);
  return `${d.getHours().toString().padStart(2,'0')}h${d.getMinutes().toString().padStart(2,'0')}`;
}

function formatReminders(reminders) {
  if (!reminders || !reminders.length) return '';
  const parts = reminders.map(r => {
    if (r.offset_type === 'weeks')   return `S-${r.offset_value}`;
    if (r.offset_type === 'days' && r.send_time) return 'J-0 matin';
    if (r.offset_type === 'days')    return `J-${r.offset_value}`;
    if (r.offset_type === 'hours')   return `H-${r.offset_value}`;
    if (r.offset_type === 'minutes') return `${r.offset_value}min`;
    return '';
  });
  return `🔔 ${parts.join(', ')}`;
}

function renderAgenda() {
  const list = document.getElementById('cal-agenda-list');
  if (!list) return;

  const today = new Date().toISOString().slice(0, 10);
  let filtered = _events.filter(e => e.date_debut >= today);

  if (_activeFilter !== 'all') {
    filtered = filtered.filter(e => e.type === _activeFilter);
  }

  filtered.sort((a, b) => a.date_debut.localeCompare(b.date_debut));

  if (!filtered.length) {
    list.innerHTML = '<div style="color:#475569;font-size:12px;padding:20px 10px">Aucun événement à venir</div>';
    return;
  }

  // Grouper par date
  const groups = {};
  for (const ev of filtered) {
    const key = ev.date_debut.slice(0, 10);
    if (!groups[key]) groups[key] = [];
    groups[key].push(ev);
  }

  list.innerHTML = '';
  for (const [dateKey, evs] of Object.entries(groups)) {
    const { label, today: isToday } = formatDateLabel(dateKey);
    const groupEl = document.createElement('div');
    groupEl.className = 'cal-day-group';
    groupEl.innerHTML = `<div class="cal-day-group-label${isToday ? ' today-label' : ''}">${label}</div>`;

    for (const ev of evs) {
      const remStr = formatReminders(ev.reminders || []);
      const card = document.createElement('div');
      card.className = 'cal-event-card';
      card.dataset.type = ev.type;
      card.innerHTML = `
        <div class="cal-event-icon">${ICONS[ev.type] || '📅'}</div>
        <div class="cal-event-body">
          <div class="cal-event-titre">${ev.titre}</div>
          <div class="cal-event-meta">${formatEventTime(ev.date_debut)}</div>
          ${remStr ? `<div class="cal-event-reminders">${remStr}</div>` : ''}
        </div>
        <div class="cal-event-actions">
          <button class="cal-edit-btn" data-id="${ev.id}" title="Éditer">✏️</button>
          <button class="cal-delete-btn" data-id="${ev.id}" title="Supprimer">🗑️</button>
        </div>
      `;
      card.querySelector('.cal-edit-btn').addEventListener('click', e => {
        e.stopPropagation();
        openModal(ev);
      });
      card.querySelector('.cal-delete-btn').addEventListener('click', e => {
        e.stopPropagation();
        confirmDelete(ev);
      });
      groupEl.appendChild(card);
    }
    list.appendChild(groupEl);
  }
}

// ── Refresh ──────────────────────────────────────────────────────────────────

async function refreshCalendar() {
  await fetchEvents();
  renderMiniGrid();
  renderAgenda();
}

// ── Modale ───────────────────────────────────────────────────────────────────

function openModal(event = null) {
  const overlay  = document.getElementById('cal-modal-overlay');
  const title    = document.getElementById('cal-modal-title');
  const idField  = document.getElementById('cal-event-id');
  const titreField = document.getElementById('cal-f-titre');
  const typeField  = document.getElementById('cal-f-type');
  const dateField  = document.getElementById('cal-f-date');
  const descField  = document.getElementById('cal-f-desc');
  const chips    = document.querySelectorAll('.cal-chip');

  // Reset chips
  chips.forEach(c => c.classList.remove('on'));

  if (event) {
    title.textContent = 'Modifier l\'événement';
    idField.value     = event.id;
    titreField.value  = event.titre || '';
    typeField.value   = event.type  || 'rdv';
    dateField.value   = event.date_debut
      ? event.date_debut.replace(' ', 'T').slice(0, 16)
      : '';
    descField.value   = event.description || '';

    // Cocher les chips correspondant aux reminders existants
    const reminders = event.reminders || [];
    chips.forEach(chip => {
      const match = reminders.find(r =>
        r.offset_type  === chip.dataset.type &&
        String(r.offset_value) === chip.dataset.value
      );
      if (match) chip.classList.add('on');
    });
  } else {
    title.textContent = 'Nouvel événement';
    idField.value     = '';
    titreField.value  = '';
    typeField.value   = 'rdv';
    dateField.value   = '';
    descField.value   = '';
  }

  overlay.classList.remove('hidden');
  titreField.focus();
}

function closeModal() {
  document.getElementById('cal-modal-overlay').classList.add('hidden');
}

async function saveModal() {
  const id    = document.getElementById('cal-event-id').value;
  const titre = document.getElementById('cal-f-titre').value.trim();
  const type  = document.getElementById('cal-f-type').value;
  const date  = document.getElementById('cal-f-date').value;
  const desc  = document.getElementById('cal-f-desc').value.trim();

  if (!titre) { alert('Le titre est requis.'); return; }
  if (!date)  { alert('La date est requise.'); return; }

  const dateDebut = date.includes('T') ? date : `${date}T00:00`;

  try {
    let eventId = id;
    if (id) {
      await updateEvent(id, { titre, type, date_debut: dateDebut, description: desc || null });
    } else {
      const created = await createEvent({ titre, type, date_debut: dateDebut, description: desc || null });
      eventId = created.id;
    }

    // Sync reminders : récupérer event actuel, supprimer anciens, ajouter nouveaux
    const currentEvent = await fetch(`${API}/calendar/events/${eventId}`).then(r => r.json());
    for (const rem of (currentEvent.reminders || [])) {
      await deleteReminder(eventId, rem.id);
    }
    const chips = document.querySelectorAll('.cal-chip.on');
    for (const chip of chips) {
      await addReminder(eventId, {
        offset_type:  chip.dataset.type,
        offset_value: parseInt(chip.dataset.value),
        send_time:    chip.dataset.sendTime || null,
      });
    }

    closeModal();
    await refreshCalendar();
  } catch (e) {
    console.error('Erreur save event:', e);
    alert('Erreur lors de la sauvegarde.');
  }
}

async function confirmDelete(event) {
  if (!confirm(`Supprimer "${event.titre}" ?`)) return;
  try {
    await deleteEvent(event.id);
    await refreshCalendar();
  } catch (e) {
    console.error('Erreur delete:', e);
    alert('Erreur lors de la suppression.');
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────

function initCalendar() {
  // Navigation mois
  document.getElementById('cal-prev').addEventListener('click', () => {
    _currentMonth--;
    if (_currentMonth < 0) { _currentMonth = 11; _currentYear--; }
    renderMiniGrid();
  });
  document.getElementById('cal-next').addEventListener('click', () => {
    _currentMonth++;
    if (_currentMonth > 11) { _currentMonth = 0; _currentYear++; }
    renderMiniGrid();
  });

  // Bouton ajouter
  document.getElementById('cal-add-btn').addEventListener('click', () => openModal());

  // Modale — fermer, annuler, sauvegarder
  document.getElementById('cal-modal-overlay').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeModal();
  });
  document.getElementById('cal-modal-cancel').addEventListener('click', closeModal);
  document.getElementById('cal-modal-save').addEventListener('click', saveModal);

  // Chips rappels
  document.querySelectorAll('.cal-chip').forEach(c => {
    c.addEventListener('click', () => c.classList.toggle('on'));
  });

  // Filtres
  document.querySelectorAll('.cal-filter').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cal-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      _activeFilter = btn.dataset.type;
      renderAgenda();
    });
  });

  // Refresh initial
  refreshCalendar();
}

// ── Export ───────────────────────────────────────────────────────────────────

window.calendarModule = {
  init: initCalendar,
  refresh: refreshCalendar,
};
