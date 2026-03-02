// API базовий URL
const API_BASE = '/api';

// Елементи DOM
const updateDataBtn = document.getElementById('update-data-btn');
const createGroupBtn = document.getElementById('create-group-btn');
const userbotsList = document.getElementById('userbots-list');
const notificationEl = document.getElementById('notification');
const totalUserbotsEl = document.getElementById('total-userbots');
const totalSessionsEl = document.getElementById('total-sessions');
const totalGroupsEl = document.getElementById('total-groups');
const sessionCountEl = document.getElementById('session-count');
const modal = document.getElementById('create-group-modal');
const modalClose = document.getElementById('modal-close');
const cancelBtn = document.getElementById('cancel-btn');
const createGroupForm = document.getElementById('create-group-form');
const adminSelect = document.getElementById('admin-userbot');
const memberCheckboxGroup = document.getElementById('member-userbots');

let availableUserbots = [];

function showNotification(message, type = 'info') {
    notificationEl.textContent = message;
    notificationEl.className = `notification ${type}`;
    notificationEl.classList.remove('hidden');

    setTimeout(() => {
        notificationEl.classList.add('hidden');
    }, 5000);
}

async function loadUserbots() {
    try {
        const response = await fetch(`${API_BASE}/userbots`);
        const data = await response.json();

        if (data.userbots.length === 0) {
            userbotsList.innerHTML = '<div class="loading">No userbots found</div>';
            totalUserbotsEl.textContent = '0';
            return;
        }

        userbotsList.innerHTML = data.userbots.map(bot => `
            <div class="userbot-item" data-id="${bot.id}">
                <div class="userbot-name">
                    ${bot.name || bot.phone_number || 'Unknown'}
                </div>
                <div class="userbot-phone">
                    ${bot.phone_number || 'No phone'}
                </div>
            </div>
        `).join('');

        totalUserbotsEl.textContent = data.userbots.length;

    } catch (error) {
        console.error('Error loading userbots:', error);
        userbotsList.innerHTML = '<div class="loading">Error loading userbots</div>';
        showNotification('No one userbot was loaded', 'error');
    }
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        totalUserbotsEl.textContent = data.total_userbots || 0;
        totalSessionsEl.textContent = data.total_sessions || 0;
        totalGroupsEl.textContent = data.total_groups || 0;
        sessionCountEl.textContent = data.total_sessions || 0;

    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function updateData() {
    try {
        updateDataBtn.disabled = true;
        updateDataBtn.innerHTML = '<span class="btn-icon">⏳</span> Updating...';

        const response = await fetch(`${API_BASE}/update-data`, {
            method: 'POST',
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(
                `Success! Added ${data.added} new userbots, skipped ${data.skipped} existing`,
                'success'
            );

            await loadUserbots();
            await loadStats();
        } else {
            showNotification(data.detail || 'Failed to update data', 'error');
        }

    } catch (error) {
        console.error('Error updating data:', error);
        showNotification('Failed to update data', 'error');
    } finally {
        updateDataBtn.disabled = false;
        updateDataBtn.innerHTML = '<span class="btn-icon">🔄</span> Update Data';
    }
}

updateDataBtn.addEventListener('click', updateData);

userbotsList.addEventListener('click', (e) => {
    const item = e.target.closest('.userbot-item');
    if (item) {
        document.querySelectorAll('.userbot-item').forEach(el => {
            el.classList.remove('active');
        });

        item.classList.add('active');

        const botId = item.dataset.id;
        console.log('Selected userbot:', botId);
    }
});

// Modal functions
function openModal() {
    modal.classList.remove('hidden');
    loadUserbotsForModal();
}

function closeModal() {
    modal.classList.add('hidden');
    createGroupForm.reset();
}

async function loadUserbotsForModal() {
    try {
        const response = await fetch(`${API_BASE}/userbots`);
        const data = await response.json();

        availableUserbots = data.userbots;

        if (availableUserbots.length === 0) {
            adminSelect.innerHTML = '<option value="">No userbots available</option>';
            memberCheckboxGroup.innerHTML = '<div class="loading">No userbots found</div>';
            return;
        }

        // Populate admin select
        adminSelect.innerHTML = '<option value="">Select admin userbot...</option>' +
            availableUserbots.map(bot => {
                const displayName = bot.name || bot.phone_number || 'Unknown';
                return `<option value="${bot.id}">${displayName}</option>`;
            }).join('');

        // Populate member checkboxes
        memberCheckboxGroup.innerHTML = availableUserbots.map(bot => {
            const displayName = bot.name || bot.phone_number || 'Unknown';
            const phone = bot.phone_number ? ` (${bot.phone_number})` : '';
            return `
                <div class="checkbox-item">
                    <input type="checkbox" id="member-${bot.id}" value="${bot.id}">
                    <label for="member-${bot.id}">${displayName}${phone}</label>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading userbots for modal:', error);
        showNotification('Failed to load userbots', 'error');
    }
}

async function createGroup(groupName, adminId, memberIds) {
    try {
        const response = await fetch(`${API_BASE}/groups/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: groupName,
                admin_id: adminId,
                member_ids: memberIds
            }),
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(
                `Group "${groupName}" created successfully!`,
                'success'
            );
            closeModal();
            await loadStats();
        } else {
            showNotification(data.detail || 'Failed to create group', 'error');
        }

    } catch (error) {
        console.error('Error creating group:', error);
        showNotification('Failed to create group', 'error');
    }
}

// Event listeners
updateDataBtn.addEventListener('click', updateData);
createGroupBtn.addEventListener('click', openModal);
modalClose.addEventListener('click', closeModal);
cancelBtn.addEventListener('click', closeModal);

createGroupForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const groupName = document.getElementById('group-name').value.trim();
    const adminId = adminSelect.value;
    const memberCheckboxes = document.querySelectorAll('#member-userbots input[type="checkbox"]:checked');
    const memberIds = Array.from(memberCheckboxes).map(cb => cb.value);

    if (!groupName) {
        showNotification('Please enter group name', 'error');
        return;
    }

    if (!adminId) {
        showNotification('Please select admin userbot', 'error');
        return;
    }

    if (memberIds.length === 0) {
        showNotification('Please select at least one member', 'error');
        return;
    }

    // Disable submit button
    const submitBtn = createGroupForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating...';

    await createGroup(groupName, adminId, memberIds);

    // Re-enable submit button
    submitBtn.disabled = false;
    submitBtn.textContent = 'Create Group';
});

// Close modal on outside click
modal.addEventListener('click', (e) => {
    if (e.target === modal) {
        closeModal();
    }
});

document.addEventListener('DOMContentLoaded', async () => {
    await loadUserbots();
    await loadStats();
});

setInterval(loadStats, 30000);
