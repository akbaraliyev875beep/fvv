/**
 * Tez Yordam EMS - History.js
 */

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    const historyList = document.getElementById('historyList');
    const loading = document.getElementById('loading');
    const emptyState = document.getElementById('emptyState');
    const totalCount = document.getElementById('totalCount');
    const rowTemplate = document.getElementById('historyRowTemplate');
    
    // Pagination
    const pagination = document.getElementById('pagination');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const currentPageSpan = document.getElementById('currentPage');
    
    let currentPage = 1;
    const limit = 10;
    let totalItems = 0;

    async function loadHistory() {
        loading.classList.remove('hidden');
        historyList.classList.add('hidden');
        emptyState.classList.add('hidden');
        pagination.classList.add('hidden');
        historyList.innerHTML = '';

        try {
            const skip = (currentPage - 1) * limit;
            const res = await fetch(`/api/v1/emergency/history?skip=${skip}&limit=${limit}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (res.ok) {
                const data = await res.json();
                totalItems = data.total;
                totalCount.textContent = totalItems;
                
                if (totalItems === 0) {
                    loading.classList.add('hidden');
                    emptyState.classList.remove('hidden');
                    return;
                }

                data.items.forEach(call => {
                    const clone = rowTemplate.content.cloneNode(true);
                    
                    // Format Date
                    const d = new Date(call.created_at);
                    clone.querySelector('.row-date').textContent = d.toLocaleDateString('uz-UZ', { day: 'numeric', month: 'long', year: 'numeric' });
                    clone.querySelector('.row-time').innerHTML = `<i class="fa-regular fa-clock mr-1"></i> ${d.toLocaleTimeString('uz-UZ', {hour: '2-digit', minute:'2-digit'})}`;
                    
                    // Status Badge
                    const badge = clone.querySelector('.status-badge');
                    badge.textContent = call.status;
                    badge.classList.add(`status-${call.status}`);
                    
                    // Icon styling
                    const iconBg = clone.querySelector('.status-icon-bg');
                    const icon = clone.querySelector('.status-icon');
                    
                    if (call.status === 'completed') {
                        iconBg.classList.add('bg-green-500/10', 'text-green-500');
                        icon.className = 'fa-solid fa-check-double status-icon text-xl';
                    } else if (call.status === 'cancelled') {
                        iconBg.classList.add('bg-red-500/10', 'text-red-500');
                        icon.className = 'fa-solid fa-ban status-icon text-xl';
                    } else {
                        iconBg.classList.add('bg-blue-500/10', 'text-blue-500');
                        icon.className = 'fa-solid fa-truck-fast status-icon text-xl';
                    }
                    
                    // Vehicle
                    if (call.brigade_vehicle) {
                        const veh = clone.querySelector('.row-vehicle');
                        veh.classList.remove('hidden');
                        veh.querySelector('.vehicle-num').textContent = call.brigade_vehicle;
                    }
                    
                    // Link
                    clone.querySelector('.view-link').href = `/sos/${call.id}`;
                    
                    historyList.appendChild(clone);
                });

                loading.classList.add('hidden');
                historyList.classList.remove('hidden');
                
                // Pagination controls
                if (totalItems > limit) {
                    pagination.classList.remove('hidden');
                    currentPageSpan.textContent = currentPage;
                    prevBtn.disabled = currentPage === 1;
                    nextBtn.disabled = currentPage * limit >= totalItems;
                }
            } else if (res.status === 401) {
                window.location.href = '/login';
            }
        } catch (e) {
            console.error(e);
            loading.innerHTML = '<p class="text-red-400">Xatolik yuz berdi</p>';
        }
    }

    prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadHistory();
        }
    });

    nextBtn.addEventListener('click', () => {
        if (currentPage * limit < totalItems) {
            currentPage++;
            loadHistory();
        }
    });

    loadHistory();
});
