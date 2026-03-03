// API базовий URL
const API_BASE = '/api';

// Елементи DOM
const updateDataBtn = document.getElementById('update-data-btn');
const createGroupBtn = document.getElementById('create-group-btn');
const contactAllBtn = document.getElementById('contact-all-btn');
const startListenersBtn = document.getElementById('start-listeners-btn');
const stopListenersBtn = document.getElementById('stop-listeners-btn');
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
const groupsList = document.getElementById('groups-list');
const editGroupPromptModal = document.getElementById('edit-group-prompt-modal');
const editGroupPromptClose = document.getElementById('edit-group-prompt-close');
const editGroupPromptCancel = document.getElementById('edit-group-prompt-cancel');
const editGroupPromptSave = document.getElementById('edit-group-prompt-save');
const editGroupPromptText = document.getElementById('edit-group-prompt-text');
const editMemberPromptModal = document.getElementById('edit-member-prompt-modal');
const editMemberPromptClose = document.getElementById('edit-member-prompt-close');
const editMemberPromptCancel = document.getElementById('edit-member-prompt-cancel');
const editMemberPromptSave = document.getElementById('edit-member-prompt-save');
const editMemberPromptText = document.getElementById('edit-member-prompt-text');

let availableUserbots = [];
let currentEditingGroupId = null;
let currentEditingMemberId = null;
let currentManagingStickersUserbotId = null;

// Stickers modal elements
const manageStickersModal = document.getElementById('manage-stickers-modal');
const manageStickersClose = document.getElementById('manage-stickers-close');
const closeStickersBtn = document.getElementById('close-stickers-btn');
const stickersUserbotName = document.getElementById('stickers-userbot-name');
const stickersList = document.getElementById('stickers-list');
const stickerFileIdInput = document.getElementById('sticker-file-id');
const stickerEmotionSelect = document.getElementById('sticker-emotion');
const addStickerBtn = document.getElementById('add-sticker-btn');

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
                <div class="userbot-trusted">
                    Trusted ID: ${bot.trusted_id || '<em>Not set</em>'}
                    <button class="btn-icon-small" onclick="editTrustedId('${bot.id}', ${bot.trusted_id || 'null'})" title="Edit trusted ID">✏️</button>
                </div>
                <div class="userbot-actions">
                    <button class="btn btn-sm btn-primary"
                            data-userbot-id="${bot.id}"
                            data-style-settings='${JSON.stringify(bot.style_settings)}'
                            onclick="editStyleSettingsFromButton(this)"
                            title="Edit style settings">
                        ⚙️ Style Settings
                    </button>
                    <button class="btn btn-sm btn-info"
                            onclick="openManageStickers('${bot.id}', '${escapeHtml(bot.name || bot.phone_number || 'Unknown')}')"
                            title="Manage stickers">
                        🎭 Stickers
                    </button>
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

async function loadGroups() {
    try {
        const response = await fetch(`${API_BASE}/groups`);
        const data = await response.json();

        if (data.groups.length === 0) {
            groupsList.innerHTML = '<div class="no-data">No groups found</div>';
            return;
        }

        groupsList.innerHTML = data.groups.map(group => `
            <div class="group-item">
                <div class="group-header">
                    <div class="group-info">
                        <h4 class="group-name">${group.name}</h4>
                        <span class="group-admin">Admin: ${group.admin_name || 'Unknown'}</span>
                        <span class="group-members-count">${group.members.length} members</span>
                        <span class="group-status ${group.is_active ? 'status-active' : 'status-inactive'}">
                            ${group.is_active ? '🟢 Active' : '🔴 Inactive'}
                        </span>
                    </div>
                    <div class="group-actions">
                        <button class="btn ${group.is_active ? 'btn-warning' : 'btn-success'}"
                                onclick="toggleGroup('${group.id}')"
                                title="${group.is_active ? 'Pause conversation' : 'Start conversation'}">
                            ${group.is_active ? '⏸️ Pause' : '▶️ Start'}
                        </button>
                        <button class="btn-icon" onclick="editGroupPrompt('${group.id}', '${escapeHtml(group.global_prompt)}')" title="Edit global prompt">
                            ✏️
                        </button>
                        <button class="btn-icon toggle-members" data-group-id="${group.id}">
                            ▼
                        </button>
                    </div>
                </div>
                <div class="group-prompt">
                    <strong>Global Prompt:</strong> ${group.global_prompt || '<em>No global prompt</em>'}
                </div>
                <div class="group-settings">
                    <strong>Settings:</strong>
                    Context: ${group.context_messages_count} msgs |
                    Delay: ${group.min_delay_seconds}-${group.max_delay_seconds}s
                </div>
                <div class="group-members hidden" id="members-${group.id}">
                    ${group.members.map(member => `
                        <div class="member-item">
                            <div class="member-info">
                                <span class="member-name">${member.userbot_name}${member.is_admin ? ' <span class="admin-badge">Admin</span>' : ''}</span>
                                <span class="member-phone">${member.phone_number || ''}</span>
                            </div>
                            <div class="member-prompt">
                                <strong>Prompt:</strong> ${member.additional_prompt || '<em>No additional prompt</em>'}
                            </div>
                            <button class="btn-icon" onclick="editMemberPrompt('${member.member_id}', '${escapeHtml(member.additional_prompt)}')" title="Edit member prompt">
                                ✏️
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');

        // Додати обробники для розгортання/згортання мемберів
        document.querySelectorAll('.toggle-members').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const groupId = e.target.dataset.groupId;
                const membersDiv = document.getElementById(`members-${groupId}`);
                membersDiv.classList.toggle('hidden');
                e.target.textContent = membersDiv.classList.contains('hidden') ? '▼' : '▲';
            });
        });

    } catch (error) {
        console.error('Error loading groups:', error);
        groupsList.innerHTML = '<div class="loading">Error loading groups</div>';
        showNotification('Failed to load groups', 'error');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function editGroupPrompt(groupId, currentPrompt) {
    currentEditingGroupId = groupId;
    editGroupPromptText.value = currentPrompt || '';
    editGroupPromptModal.classList.remove('hidden');
}

function closeEditGroupPromptModal() {
    editGroupPromptModal.classList.add('hidden');
    currentEditingGroupId = null;
}

async function saveGroupPrompt() {
    if (!currentEditingGroupId) return;

    try {
        const response = await fetch(`${API_BASE}/groups/${currentEditingGroupId}/prompt`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                global_prompt: editGroupPromptText.value
            })
        });

        if (response.ok) {
            showNotification('Group prompt updated successfully', 'success');
            closeEditGroupPromptModal();
            await loadGroups();
        } else {
            const data = await response.json();
            showNotification(data.detail || 'Failed to update group prompt', 'error');
        }
    } catch (error) {
        console.error('Error updating group prompt:', error);
        showNotification('Failed to update group prompt', 'error');
    }
}

function editMemberPrompt(memberId, currentPrompt) {
    currentEditingMemberId = memberId;
    editMemberPromptText.value = currentPrompt || '';
    editMemberPromptModal.classList.remove('hidden');
}

function closeEditMemberPromptModal() {
    editMemberPromptModal.classList.add('hidden');
    currentEditingMemberId = null;
}

async function saveMemberPrompt() {
    if (!currentEditingMemberId) return;

    try {
        const response = await fetch(`${API_BASE}/members/${currentEditingMemberId}/prompt`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                additional_prompt: editMemberPromptText.value
            })
        });

        if (response.ok) {
            showNotification('Member prompt updated successfully', 'success');
            closeEditMemberPromptModal();
            await loadGroups();
        } else {
            const data = await response.json();
            showNotification(data.detail || 'Failed to update member prompt', 'error');
        }
    } catch (error) {
        console.error('Error updating member prompt:', error);
        showNotification('Failed to update member prompt', 'error');
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

async function createGroup(groupName, adminId, memberIds, globalPrompt = "", conversationSettings = {}) {
    try {
        const response = await fetch(`${API_BASE}/groups/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: groupName,
                admin_id: adminId,
                member_ids: memberIds,
                global_prompt: globalPrompt,
                ...conversationSettings
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
    const globalPrompt = document.getElementById('global-prompt').value.trim();
    const adminId = adminSelect.value;
    const memberCheckboxes = document.querySelectorAll('#member-userbots input[type="checkbox"]:checked');
    const memberIds = Array.from(memberCheckboxes).map(cb => cb.value);

    // Get conversation settings
    const contextMessages = parseInt(document.getElementById('context-messages').value) || 10;
    const minDelay = parseInt(document.getElementById('min-delay').value) || 10;
    const maxDelay = parseInt(document.getElementById('max-delay').value) || 40;

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

    if (minDelay > maxDelay) {
        showNotification('Min delay must be less than or equal to max delay', 'error');
        return;
    }

    // Disable submit button
    const submitBtn = createGroupForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating...';

    const conversationSettings = {
        context_messages_count: contextMessages,
        min_delay_seconds: minDelay,
        max_delay_seconds: maxDelay
    };

    await createGroup(groupName, adminId, memberIds, globalPrompt, conversationSettings);

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

// Group Conversation Management
async function toggleGroup(groupId) {
    try {
        const response = await fetch(`${API_BASE}/groups/${groupId}/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(data.message, 'success');
            await loadGroups();
        } else {
            showNotification(data.detail || 'Failed to toggle group', 'error');
        }
    } catch (error) {
        console.error('Error toggling group:', error);
        showNotification('Failed to toggle group', 'error');
    }
}

// Trusted ID Management
async function editTrustedId(userbotId, currentTrustedId) {
    const newTrustedId = prompt('Enter Trusted ID (Telegram user ID):', currentTrustedId || '');

    if (newTrustedId === null) return; // User cancelled

    try {
        const response = await fetch(`${API_BASE}/userbots/${userbotId}/trusted-id`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                trusted_id: newTrustedId || null
            })
        });

        if (response.ok) {
            showNotification('Trusted ID updated successfully', 'success');
            await loadUserbots();
        } else {
            const data = await response.json();
            showNotification(data.detail || 'Failed to update trusted ID', 'error');
        }
    } catch (error) {
        console.error('Error updating trusted ID:', error);
        showNotification('Failed to update trusted ID', 'error');
    }
}

// Listeners Management
async function startListeners() {
    try {
        startListenersBtn.disabled = true;
        startListenersBtn.innerHTML = '<span class="btn-icon">⏳</span> Starting...';

        const response = await fetch(`${API_BASE}/listeners/start`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`Listeners started! Active: ${data.active_listeners}`, 'success');
            startListenersBtn.style.display = 'none';
            stopListenersBtn.style.display = 'inline-block';
        } else {
            showNotification(data.detail || 'Failed to start listeners', 'error');
        }
    } catch (error) {
        console.error('Error starting listeners:', error);
        showNotification('Failed to start listeners', 'error');
    } finally {
        startListenersBtn.disabled = false;
        startListenersBtn.innerHTML = '<span class="btn-icon">▶️</span> Start Listeners';
    }
}

async function stopListeners() {
    try {
        stopListenersBtn.disabled = true;
        stopListenersBtn.innerHTML = '<span class="btn-icon">⏳</span> Stopping...';

        const response = await fetch(`${API_BASE}/listeners/stop`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Listeners stopped successfully', 'success');
            stopListenersBtn.style.display = 'none';
            startListenersBtn.style.display = 'inline-block';
        } else {
            showNotification(data.detail || 'Failed to stop listeners', 'error');
        }
    } catch (error) {
        console.error('Error stopping listeners:', error);
        showNotification('Failed to stop listeners', 'error');
    } finally {
        stopListenersBtn.disabled = false;
        stopListenersBtn.innerHTML = '<span class="btn-icon">⏹️</span> Stop Listeners';
    }
}

async function checkListenersStatus() {
    try {
        const response = await fetch(`${API_BASE}/listeners/status`);
        const data = await response.json();

        if (data.active_listeners > 0) {
            startListenersBtn.style.display = 'none';
            stopListenersBtn.style.display = 'inline-block';
        } else {
            startListenersBtn.style.display = 'inline-block';
            stopListenersBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking listeners status:', error);
    }
}

// Listeners Event Listeners
startListenersBtn.addEventListener('click', startListeners);
stopListenersBtn.addEventListener('click', stopListeners);

// Edit Group Prompt Modal Event Listeners
editGroupPromptClose.addEventListener('click', closeEditGroupPromptModal);
editGroupPromptCancel.addEventListener('click', closeEditGroupPromptModal);
editGroupPromptSave.addEventListener('click', saveGroupPrompt);

editGroupPromptModal.addEventListener('click', (e) => {
    if (e.target === editGroupPromptModal) {
        closeEditGroupPromptModal();
    }
});

// Edit Member Prompt Modal Event Listeners
editMemberPromptClose.addEventListener('click', closeEditMemberPromptModal);
editMemberPromptCancel.addEventListener('click', closeEditMemberPromptModal);
editMemberPromptSave.addEventListener('click', saveMemberPrompt);

editMemberPromptModal.addEventListener('click', (e) => {
    if (e.target === editMemberPromptModal) {
        closeEditMemberPromptModal();
    }
});

document.addEventListener('DOMContentLoaded', async () => {
    await loadUserbots();
    await loadStats();
    await loadGroups();
    await checkListenersStatus();
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


// Style Settings Management
const editStyleModal = document.getElementById('edit-style-modal');
const editStyleClose = document.getElementById('edit-style-close');
const editStyleCancel = document.getElementById('edit-style-cancel');
const editStyleSave = document.getElementById('edit-style-save');

let currentEditingUserbotId = null;

function editStyleSettingsFromButton(button) {
    const userbotId = button.dataset.userbotId;
    const currentSettings = JSON.parse(button.dataset.styleSettings);
    editStyleSettings(userbotId, currentSettings);
}

function editStyleSettings(userbotId, currentSettings) {
    currentEditingUserbotId = userbotId;

    // Fill form with current settings
    document.getElementById('style-allow-profanity').checked = currentSettings.allow_profanity || false;
    document.getElementById('style-use-punctuation').checked = currentSettings.use_punctuation !== false;
    document.getElementById('style-use-uppercase').checked = currentSettings.use_uppercase !== false;
    document.getElementById('style-send-photos').checked = currentSettings.send_photos || false;
    document.getElementById('style-gender').value = currentSettings.gender || 'male';
    document.getElementById('style-language').value = currentSettings.language || 'ukrainian';
    document.getElementById('style-send-stickers').checked = currentSettings.send_stickers || false;
    document.getElementById('style-use-ascii-emoticons').checked = currentSettings.use_ascii_emoticons || false;

    // Set emoji probability slider and display
    const emojiProbability = currentSettings.emoji_probability || 0;
    document.getElementById('style-emoji-probability').value = emojiProbability;
    document.getElementById('emoji-probability-value').textContent = `${emojiProbability}%`;

    // Set new slang and typo settings
    document.getElementById('style-use-youth-slang').checked = currentSettings.use_youth_slang || false;
    document.getElementById('style-use-illiterate-slang').checked = currentSettings.use_illiterate_slang || false;
    document.getElementById('style-use-typos').checked = currentSettings.use_typos || false;

    document.getElementById('style-message-length').value = currentSettings.message_length || 'medium';

    editStyleModal.classList.remove('hidden');
}

function closeStyleModal() {
    editStyleModal.classList.add('hidden');
    currentEditingUserbotId = null;
}

async function saveStyleSettings() {
    if (!currentEditingUserbotId) return;
    
    const styleSettings = {
        allow_profanity: document.getElementById('style-allow-profanity').checked,
        use_punctuation: document.getElementById('style-use-punctuation').checked,
        use_uppercase: document.getElementById('style-use-uppercase').checked,
        send_photos: document.getElementById('style-send-photos').checked,
        gender: document.getElementById('style-gender').value,
        language: document.getElementById('style-language').value,
        send_stickers: document.getElementById('style-send-stickers').checked,
        use_ascii_emoticons: document.getElementById('style-use-ascii-emoticons').checked,
        emoji_probability: parseInt(document.getElementById('style-emoji-probability').value) || 0,
        use_youth_slang: document.getElementById('style-use-youth-slang').checked,
        use_illiterate_slang: document.getElementById('style-use-illiterate-slang').checked,
        use_typos: document.getElementById('style-use-typos').checked,
        message_length: document.getElementById('style-message-length').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/userbots/${currentEditingUserbotId}/style-settings`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                style_settings: styleSettings
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Style settings updated successfully', 'success');
            closeStyleModal();
            await loadUserbots();
        } else {
            showNotification(data.detail || 'Failed to update style settings', 'error');
        }
    } catch (error) {
        console.error('Error updating style settings:', error);
        showNotification('Failed to update style settings', 'error');
    }
}

editStyleClose.addEventListener('click', closeStyleModal);
editStyleCancel.addEventListener('click', closeStyleModal);
editStyleSave.addEventListener('click', saveStyleSettings);

// Update emoji probability display when slider moves
document.getElementById('style-emoji-probability').addEventListener('input', (e) => {
    document.getElementById('emoji-probability-value').textContent = `${e.target.value}%`;
});

editStyleModal.addEventListener('click', (e) => {
    if (e.target === editStyleModal) {
        closeStyleModal();
    }
});

// ==================== STICKERS MANAGEMENT ====================

async function openManageStickers(userbotId, userbotName) {
    currentManagingStickersUserbotId = userbotId;
    stickersUserbotName.textContent = userbotName;

    // Clear inputs
    stickerFileIdInput.value = '';
    stickerEmotionSelect.value = 'laughter';

    // Show modal
    manageStickersModal.classList.remove('hidden');

    // Load stickers
    await loadStickers(userbotId);
}

function closeManageStickers() {
    manageStickersModal.classList.add('hidden');
    currentManagingStickersUserbotId = null;
}

async function loadStickers(userbotId) {
    try {
        stickersList.innerHTML = '<div class="loading">Loading stickers...</div>';

        const response = await fetch(`${API_BASE}/stickers/${userbotId}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to load stickers');
        }

        if (data.stickers.length === 0) {
            stickersList.innerHTML = '<div class="no-data">No stickers added yet</div>';
            return;
        }

        // Group by emotion
        const groupedStickers = {};
        data.stickers.forEach(sticker => {
            if (!groupedStickers[sticker.emotion]) {
                groupedStickers[sticker.emotion] = [];
            }
            groupedStickers[sticker.emotion].push(sticker);
        });

        // Render grouped stickers
        stickersList.innerHTML = Object.entries(groupedStickers).map(([emotion, stickers]) => `
            <div class="sticker-group">
                <div class="sticker-group-header">${getEmotionEmoji(emotion)} ${emotion} (${stickers.length})</div>
                <div class="sticker-items">
                    ${stickers.map(sticker => `
                        <div class="sticker-item">
                            <div class="sticker-info">
                                <code class="sticker-file-id">${sticker.file_id}</code>
                            </div>
                            <button class="btn-icon-small btn-danger"
                                    onclick="deleteSticker('${sticker.id}')"
                                    title="Delete sticker">
                                🗑️
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading stickers:', error);
        stickersList.innerHTML = '<div class="error">Error loading stickers</div>';
        showNotification('Failed to load stickers', 'error');
    }
}

function getEmotionEmoji(emotion) {
    const emojis = {
        'laughter': '😂',
        'sad': '😢',
        'angry': '😠',
        'love': '❤️',
        'surprised': '😮',
        'confused': '😕',
        'happy': '😊',
        'thinking': '🤔',
        'crying': '😭',
        'cool': '😎'
    };
    return emojis[emotion] || '🎭';
}

async function addSticker() {
    const fileId = stickerFileIdInput.value.trim();
    const emotion = stickerEmotionSelect.value;

    if (!fileId) {
        showNotification('Please enter a file_id', 'error');
        return;
    }

    if (!currentManagingStickersUserbotId) {
        showNotification('No userbot selected', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/stickers`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                userbot_id: currentManagingStickersUserbotId,
                file_id: fileId,
                emotion: emotion
            })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Sticker added successfully', 'success');
            stickerFileIdInput.value = '';
            await loadStickers(currentManagingStickersUserbotId);
        } else {
            showNotification(data.detail || 'Failed to add sticker', 'error');
        }
    } catch (error) {
        console.error('Error adding sticker:', error);
        showNotification('Failed to add sticker', 'error');
    }
}

async function deleteSticker(stickerId) {
    if (!confirm('Are you sure you want to delete this sticker?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/stickers/${stickerId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Sticker deleted successfully', 'success');
            await loadStickers(currentManagingStickersUserbotId);
        } else {
            showNotification(data.detail || 'Failed to delete sticker', 'error');
        }
    } catch (error) {
        console.error('Error deleting sticker:', error);
        showNotification('Failed to delete sticker', 'error');
    }
}

// Event listeners for stickers modal
manageStickersClose.addEventListener('click', closeManageStickers);
closeStickersBtn.addEventListener('click', closeManageStickers);
addStickerBtn.addEventListener('click', addSticker);

manageStickersModal.addEventListener('click', (e) => {
    if (e.target === manageStickersModal) {
        closeManageStickers();
    }
});
