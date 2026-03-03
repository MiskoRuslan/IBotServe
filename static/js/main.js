// API базовий URL
const API_BASE = '/api';

// Елементи DOM
const updateDataBtn = document.getElementById('update-data-btn');
const createGroupBtn = document.getElementById('create-group-btn');
const contactAllBtn = document.getElementById('contact-all-btn');
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
const progressModal = document.getElementById('contact-progress-modal');
const progressModalClose = document.getElementById('progress-modal-close');
const progressCloseBtn = document.getElementById('progress-close-btn');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const progressPercentage = document.getElementById('progress-percentage');
const currentUserbotEl = document.getElementById('current-userbot');
const progressCountEl = document.getElementById('progress-count');
const successCountEl = document.getElementById('success-count');
const skippedCountEl = document.getElementById('skipped-count');
const errorCountEl = document.getElementById('error-count');
const progressLog = document.getElementById('progress-log');

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

// Contact All Progress Modal Functions
function openProgressModal() {
    progressModal.classList.remove('hidden');
    progressModalClose.disabled = true;
    progressCloseBtn.disabled = true;

    progressBar.style.width = '0%';
    progressText.textContent = 'Initializing...';
    progressPercentage.textContent = '0%';
    currentUserbotEl.textContent = '-';
    progressCountEl.textContent = '0 / 0';
    successCountEl.textContent = '0';
    skippedCountEl.textContent = '0';
    errorCountEl.textContent = '0';
    progressLog.innerHTML = '';
}

function closeProgressModal() {
    progressModal.classList.add('hidden');
}

function addProgressLog(message, type = 'info') {
    const logEntry = document.createElement('div');
    logEntry.className = `progress-log-entry ${type}`;
    logEntry.textContent = message;
    progressLog.appendChild(logEntry);
    progressLog.scrollTop = progressLog.scrollHeight;
}

async function startContactAll() {
    try {
        contactAllBtn.disabled = true;
        contactAllBtn.innerHTML = '<span class="btn-icon">⏳</span> Processing...';

        openProgressModal();

        const eventSource = new EventSource(`${API_BASE}/contacts/add-all`);

        let totalUserbots = 0;
        let successCount = 0;
        let skippedCount = 0;
        let errorCount = 0;

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);

            switch(data.type) {
                case 'started':
                    totalUserbots = data.total_userbots;
                    progressText.textContent = data.message;
                    progressCountEl.textContent = `0 / ${totalUserbots}`;
                    addProgressLog(data.message, 'info');
                    break;

                case 'processing_userbot':
                    const percentage = Math.round((data.current / data.total) * 100);
                    progressBar.style.width = `${percentage}%`;
                    progressPercentage.textContent = `${percentage}%`;
                    currentUserbotEl.textContent = data.userbot_name;
                    progressCountEl.textContent = `${data.current} / ${data.total}`;
                    progressText.textContent = `Processing ${data.userbot_name}...`;
                    addProgressLog(`Processing: ${data.userbot_name}`, 'info');
                    break;

                case 'userbot_completed':
                    successCount++;
                    successCountEl.textContent = successCount;
                    addProgressLog(`✓ ${data.userbot_name}: Added ${data.added} contacts`, 'success');
                    break;

                case 'userbot_skipped':
                    skippedCount++;
                    skippedCountEl.textContent = skippedCount;
                    addProgressLog(`⊘ ${data.userbot_name}: ${data.reason}`, 'warning');
                    break;

                case 'userbot_error':
                    errorCount++;
                    errorCountEl.textContent = errorCount;
                    addProgressLog(`✗ ${data.userbot_name}: ${data.error}`, 'error');
                    break;

                case 'completed':
                    progressBar.style.width = '100%';
                    progressPercentage.textContent = '100%';
                    progressText.textContent = data.message;
                    addProgressLog(data.message, 'success');

                    progressModalClose.disabled = false;
                    progressCloseBtn.disabled = false;

                    showNotification(
                        `Contact all completed! Success: ${data.success}, Skipped: ${data.skipped}, Errors: ${data.errors}`,
                        data.errors > 0 ? 'warning' : 'success'
                    );

                    eventSource.close();
                    break;

                case 'error':
                    progressText.textContent = 'Error occurred';
                    addProgressLog(`Error: ${data.message}`, 'error');
                    progressModalClose.disabled = false;
                    progressCloseBtn.disabled = false;
                    showNotification(data.message, 'error');
                    eventSource.close();
                    break;
            }
        };

        eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            addProgressLog('Connection error occurred', 'error');
            progressModalClose.disabled = false;
            progressCloseBtn.disabled = false;
            showNotification('Connection error during contact all', 'error');
            eventSource.close();
        };

    } catch (error) {
        console.error('Error starting contact all:', error);
        showNotification('Failed to start contact all', 'error');
        closeProgressModal();
    } finally {
        contactAllBtn.disabled = false;
        contactAllBtn.innerHTML = '<span class="btn-icon">📞</span> Contact All';
    }
}

// Contact All Event Listeners
contactAllBtn.addEventListener('click', startContactAll);
progressModalClose.addEventListener('click', closeProgressModal);
progressCloseBtn.addEventListener('click', closeProgressModal);

progressModal.addEventListener('click', (e) => {
    if (e.target === progressModal && !progressCloseBtn.disabled) {
        closeProgressModal();
    }
});
