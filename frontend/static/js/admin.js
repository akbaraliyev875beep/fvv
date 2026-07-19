z/**
 * Tez Yordam EMS - Admin.js
 */

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    // Navigation
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.content-section');
    let servicesCache = [];

    async function loadServices() {
        try {
            const res = await fetch('/api/v1/services/');
            if (res.ok) {
                servicesCache = await res.json();
                const select = document.getElementById('inputServiceType');
                if (select) {
                    servicesCache.forEach(svc => {
                        const opt = document.createElement('option');
                        opt.value = svc.id;
                        opt.textContent = svc.name_uz;
                        select.appendChild(opt);
                    });
                }
            }
        } catch (e) { console.error(e); }
    }

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Update active state
            navLinks.forEach(l => {
                l.classList.remove('bg-white/10', 'text-white');
                l.classList.add('hover:bg-white/5', 'text-gray-400');
            });
            link.classList.remove('hover:bg-white/5', 'text-gray-400');
            link.classList.add('bg-white/10', 'text-white');

            // Show section
            const targetId = link.getAttribute('data-target');
            sections.forEach(s => s.classList.add('hidden'));
            document.getElementById(targetId).classList.remove('hidden');

            // Load data based on section
            if (targetId === 'usersSection') loadUsers();
            if (targetId === 'brigadesSection') loadBrigades();
        });
    });

    // ── STATS ────────────────────────────────────────────────────────
    async function loadStats() {
        try {
            const res = await fetch('/api/v1/emergency/stats', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                document.getElementById('statTotal').textContent = data.total_calls_today;
                document.getElementById('statActive').textContent = data.active_calls;
                document.getElementById('statBrigades').textContent = data.available_brigades;
                document.getElementById('statAvg').textContent = data.average_response_time_mins || 0;
            }
        } catch (e) { console.error(e); }
    }

    // ── USERS ────────────────────────────────────────────────────────
    const usersTableBody = document.getElementById('usersTableBody');
    
    async function loadUsers() {
        usersTableBody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-gray-500">Yuklanmoqda...</td></tr>';
        try {
            const res = await fetch('/api/v1/auth/users', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const users = await res.json();
                usersTableBody.innerHTML = '';
                users.forEach(user => {
                    const d = new Date(user.created_at);
                    const tr = document.createElement('tr');
                    tr.className = 'hover:bg-white/5 transition-colors group';
                    tr.innerHTML = `
                        <td class="px-6 py-4">
                            <div class="font-bold text-white">${user.full_name}</div>
                            <div class="text-[10px] text-gray-500 font-mono">${user.id}</div>
                        </td>
                        <td class="px-6 py-4 text-gray-300">${user.phone}</td>
                        <td class="px-6 py-4">
                            <span class="px-2.5 py-1 rounded-md text-xs font-bold ${getRoleBadge(user.role)}">${user.role.toUpperCase()}</span>
                        </td>
                        <td class="px-6 py-4 text-gray-400 text-sm">${d.toLocaleDateString('uz-UZ')}</td>
                        <td class="px-6 py-4 text-right">
                            <select onchange="updateUserRole('${user.id}', this.value)" class="bg-black/40 border border-white/10 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-500 text-white [&>option]:bg-dark opacity-0 group-hover:opacity-100 transition-opacity">
                                <option value="patient" ${user.role==='patient'?'selected':''}>Patient</option>
                                <option value="dispatcher" ${user.role==='dispatcher'?'selected':''}>Dispatcher</option>
                                <option value="brigade" ${user.role==='brigade'?'selected':''}>Brigade</option>
                                <option value="admin" ${user.role==='admin'?'selected':''}>Admin</option>
                            </select>
                        </td>
                    `;
                    usersTableBody.appendChild(tr);
                });
            } else {
                usersTableBody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-red-400">Xatolik yoki ruxsat yo\'q</td></tr>';
            }
        } catch (e) { console.error(e); }
    }

    function getRoleBadge(role) {
        if(role==='admin') return 'bg-purple-500/20 text-purple-400 border border-purple-500/30';
        if(role==='dispatcher') return 'bg-blue-500/20 text-blue-400 border border-blue-500/30';
        if(role==='brigade') return 'bg-red-500/20 text-red-400 border border-red-500/30';
        return 'bg-gray-500/20 text-gray-400 border border-gray-500/30';
    }

    window.updateUserRole = async function(id, role) {
        try {
            const res = await fetch(`/api/v1/auth/users/${id}/role`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ role })
            });
            if (res.ok) {
                loadUsers();
            } else {
                alert("Xatolik yuz berdi");
                loadUsers();
            }
        } catch (e) { console.error(e); }
    }


    // ── BRIGADES ─────────────────────────────────────────────────────
    const brigadesGrid = document.getElementById('brigadesGrid');
    const brigadeModal = document.getElementById('brigadeModal');
    const brigadeForm = document.getElementById('brigadeForm');
    
    async function loadBrigades() {
        brigadesGrid.innerHTML = '<div class="col-span-3 text-center py-4 text-gray-500">Yuklanmoqda...</div>';
        try {
            const res = await fetch('/api/v1/dispatcher/brigades', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const brigades = await res.json();
                brigadesGrid.innerHTML = '';
                brigades.forEach(b => {
                    const div = document.createElement('div');
                    div.className = 'glass-card p-5 rounded-2xl border border-white/10 flex flex-col group';
                    div.innerHTML = `
                        <div class="flex justify-between items-start mb-4">
                            <div class="w-12 h-12 bg-blue-500/10 text-blue-400 rounded-xl flex items-center justify-center border border-blue-500/20">
                                <i class="fa-solid fa-truck-medical text-xl"></i>
                            </div>
                            <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button onclick="deleteBrigade('${b.id}')" class="w-8 h-8 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 flex items-center justify-center transition-colors">
                                    <i class="fa-solid fa-trash text-xs"></i>
                                </button>
                            </div>
                        </div>
                        <h4 class="text-xl font-bold text-white mb-1">${b.vehicle_number}</h4>
                        <div class="text-xs text-gray-500 font-mono mb-4">ID: ${b.id.substring(0,8)}...</div>
                        
                        <div class="mt-auto flex justify-between items-center pt-4 border-t border-white/5">
                            <span class="status-badge status-${b.status}">${b.status.toUpperCase()}</span>
                            ${b.service_type_id ? (() => {
                                const svc = servicesCache.find(s => s.id === b.service_type_id);
                                return svc ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold" style="background-color: ${svc.color_hex}30; color: ${svc.color_hex}">${svc.name_uz}</span>` : '';
                            })() : '<span class="text-[10px] text-gray-500 font-bold uppercase">Umumiy</span>'}
                        </div>
                    `;
                    brigadesGrid.appendChild(div);
                });
            } else {
                brigadesGrid.innerHTML = '<div class="col-span-3 text-center py-4 text-red-400">Xatolik yuz berdi</div>';
            }
        } catch(e) { console.error(e); }
    }

    window.openBrigadeModal = function() {
        brigadeModal.classList.remove('hidden');
        setTimeout(() => {
            brigadeModal.classList.remove('opacity-0');
            document.getElementById('brigadeModalContent').classList.remove('scale-95');
        }, 10);
    }

    window.closeBrigadeModal = function() {
        brigadeModal.classList.add('opacity-0');
        document.getElementById('brigadeModalContent').classList.add('scale-95');
        setTimeout(() => {
            brigadeModal.classList.add('hidden');
            brigadeForm.reset();
        }, 300);
    }

    brigadeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const vNum = document.getElementById('inputVehicle').value;
        const status = document.getElementById('inputStatus').value;
        const svcId = document.getElementById('inputServiceType').value;
        
        const payload = { vehicle_number: vNum, status };
        if (svcId) {
            payload.service_type_id = svcId;
        }
        
        try {
            const res = await fetch('/api/v1/dispatcher/brigades', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });
            
            if (res.ok) {
                closeBrigadeModal();
                loadBrigades();
            } else {
                const err = await res.json();
                alert(err.detail || "Xatolik yuz berdi");
            }
        } catch(e) { console.error(e); }
    });

    window.deleteBrigade = async function(id) {
        if(!confirm("Brigadani o'chirishni tasdiqlaysizmi?")) return;
        try {
            const res = await fetch(`/api/v1/dispatcher/brigades/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                loadBrigades();
            } else {
                alert("Xatolik yuz berdi");
            }
        } catch(e) { console.error(e); }
    }

    window.logout = function() {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
    }

    // Init
    loadServices().then(() => {
        loadStats();
        // optionally load default active tab
        loadUsers();
    });
});
