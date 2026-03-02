// API базовий URL
const API_BASE = '/api';

// Елементи DOM
const updateDataBtn = document.getElementById('update-data-btn');
const userbotsList = document.getElementById('userbots-list');
const notificationEl = document.getElementById('notification');
const totalUserbotsEl = document.getElementById('total-userbots');
const totalSessionsEl = document.getElementById('total-sessions');
const totalGroupsEl = document.getElementById('total-groups');
const sessionCountEl = document.getElementById('session-count');

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

document.addEventListener('DOMContentLoaded', async () => {
    await loadUserbots();
    await loadStats();
});

setInterval(loadStats, 30000);
