/**
 * Tez Yordam EMS - Dashboard.js
 * Dispetcher interfeysi mantig'i
 */

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    // Leaflet Map Setup
    const map = L.map('map', { zoomControl: false }).setView([41.2995, 69.2401], 12);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png').addTo(map);

    const callIcon = L.divIcon({
        className: 'custom-div-icon',
        html: `<div class="w-4 h-4 bg-red-500 rounded-full border-2 border-white shadow-[0_0_15px_rgba(239,68,68,0.8)] marker-pulse"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
    });

    let calls = [];
    let activeMarkers = {};
    let activeServiceType = "";
    let servicesCache = [];

    // DOM Elements
    const callsList = document.getElementById('callsList');
    const callCardTemplate = document.getElementById('callCardTemplate');
    const assignmentPanel = document.getElementById('assignmentPanel');
    const assignCallId = document.getElementById('assignCallId');
    const brigadesList = document.getElementById('brigadesList');
    const brigadeRowTemplate = document.getElementById('brigadeRowTemplate');
    
    // Stats
    const statActive = document.getElementById('statActive');
    const statBrigades = document.getElementById('statBrigades');

    let currentAssignCallId = null;

    // Initialize
    async function init() {
        await loadServices();
        await loadStats();
        await loadCalls();
        connectWebSocket();
    }

    async function loadServices() {
        try {
            const res = await fetch('/api/v1/services/');
            if (res.ok) {
                servicesCache = await res.json();
                renderServiceFilters();
            }
        } catch (e) {
            console.error("Xizmatlarni yuklashda xatolik:", e);
        }
    }

    function renderServiceFilters() {
        const container = document.getElementById('serviceFilters');
        if (!container) return;
        
        container.innerHTML = `<button class="px-3 py-1.5 bg-white/20 text-white rounded-md text-xs font-medium shrink-0 transition-colors filter-btn" data-service="">Hammasi</button>`;
        
        servicesCache.forEach(svc => {
            container.innerHTML += `
                <button class="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white rounded-md text-xs font-medium shrink-0 flex items-center gap-1.5 transition-colors filter-btn" data-service="${svc.code}">
                    <div class="w-2 h-2 rounded-full" style="background-color: ${svc.color_hex}"></div>
                    ${svc.name_uz}
                </button>
            `;
        });

        // Add click events
        container.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Update UI
                container.querySelectorAll('.filter-btn').forEach(b => {
                    b.classList.remove('bg-white/20', 'text-white');
                    b.classList.add('bg-white/5', 'text-gray-300');
                });
                const currentBtn = e.currentTarget;
                currentBtn.classList.remove('bg-white/5', 'text-gray-300');
                currentBtn.classList.add('bg-white/20', 'text-white');
                
                // Update state and reload
                activeServiceType = currentBtn.dataset.service;
                loadCalls();
                
                // Reconnect WS if needed (or just filter locally)
                connectWebSocket();
            });
        });
    }

    async function loadStats() {
        try {
            const res = await fetch('/api/v1/emergency/stats', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                statActive.textContent = data.active_calls;
                statBrigades.textContent = data.available_brigades;
            }
        } catch (e) { console.error(e); }
    }

    async function loadCalls() {
        try {
            callsList.innerHTML = '<div class="text-center py-10"><i class="fa-solid fa-spinner fa-spin text-2xl mb-2"></i></div>';
            let url = '/api/v1/emergency/active/list?limit=100';
            if (activeServiceType) {
                url += `&service_type=${activeServiceType}`;
            }
            
            const res = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                calls = data.items;
                renderCalls();
            }
        } catch (e) {
            callsList.innerHTML = '<div class="text-center text-red-400 p-4">Xatolik yuz berdi</div>';
        }
    }

    function renderCalls() {
        callsList.innerHTML = '';
        
        // Clear old markers
        Object.values(activeMarkers).forEach(m => map.removeLayer(m));
        activeMarkers = {};

        if (calls.length === 0) {
            callsList.innerHTML = `
                <div class="text-center text-gray-500 py-10">
                    <i class="fa-solid fa-check-double text-3xl mb-3 opacity-50"></i>
                    <p>Faol chaqiruvlar yo'q</p>
                </div>
            `;
            return;
        }

        calls.forEach(call => {
            const clone = callCardTemplate.content.cloneNode(true);
            const card = clone.querySelector('.call-card');
            
            // Set text
            clone.querySelector('.patient-name').textContent = call.patient_name || 'Noma\'lum bemor';
            clone.querySelector('.description').textContent = call.transcript || 'Ma\'lumot yo\'q';
            clone.querySelector('.time-ago').textContent = getTimeAgo(call.created_at);
            
            // Status badge
            const badge = clone.querySelector('.status-badge');
            badge.textContent = call.status.toUpperCase();
            badge.classList.add(`status-${call.status}`);
            
            // Service badge
            if (call.service_type_id) {
                const svcBadge = clone.querySelector('.service-badge');
                const svc = servicesCache.find(s => s.id === call.service_type_id);
                if (svc) {
                    svcBadge.classList.remove('hidden');
                    svcBadge.textContent = svc.name_uz;
                    svcBadge.style.backgroundColor = svc.color_hex + '30';
                    svcBadge.style.color = svc.color_hex;
                }
            }
            
            // Multi-service badge
            if (call.is_multi_service || call.parent_call_id) {
                const multiBadge = document.createElement('span');
                multiBadge.className = 'px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider bg-purple-500/20 text-purple-400 border border-purple-500/30';
                multiBadge.innerHTML = '<i class="fa-solid fa-layer-group"></i> Multi';
                clone.querySelector('.flex.gap-2').appendChild(multiBadge);
            }
            
            // Risk badge
            if (call.risk_level) {
                const riskBadge = clone.querySelector('.risk-badge');
                riskBadge.classList.remove('hidden');
                riskBadge.textContent = call.risk_level;
                
                if (call.risk_level === 'CRITICAL') {
                    riskBadge.classList.add('bg-red-500/20', 'text-red-400', 'border-red-500/30');
                    card.querySelector('.pulse-bg').classList.remove('hidden');
                } else if (call.risk_level === 'HIGH') {
                    riskBadge.classList.add('bg-orange-500/20', 'text-orange-400', 'border-orange-500/30');
                } else if (call.risk_level === 'MEDIUM') {
                    riskBadge.classList.add('bg-yellow-500/20', 'text-yellow-400', 'border-yellow-500/30');
                } else {
                    riskBadge.classList.add('bg-green-500/20', 'text-green-400', 'border-green-500/30');
                }
            }

            // Click handler
            card.addEventListener('click', () => {
                if (call.latitude && call.longitude) {
                    map.setView([call.latitude, call.longitude], 15);
                }
                if (call.status === 'pending') {
                    openAssignmentPanel(call);
                }
            });

            callsList.appendChild(clone);

            // Add marker
            if (call.latitude && call.longitude) {
                const m = L.marker([call.latitude, call.longitude], {icon: callIcon}).addTo(map);
                m.bindPopup(`<b>${call.patient_name || 'Bemor'}</b><br>${call.status}`);
                activeMarkers[call.id] = m;
            }
        });
    }

    // Assignment Panel
    window.openAssignmentPanel = async function(call) {
        currentAssignCallId = call.id;
        assignCallId.textContent = `Call ID: ${call.id.substring(0,8)}...`;
        
        // AI insights
        const aiBox = document.getElementById('aiInsights');
        if (call.recommended_action) {
            aiBox.classList.remove('hidden');
            document.getElementById('aiReasoning').textContent = call.recommended_action;
        } else {
            aiBox.classList.add('hidden');
        }

        // Multi-service info
        const multiBox = document.getElementById('multiServiceInfo');
        if (call.is_multi_service || call.parent_call_id) {
            multiBox.classList.remove('hidden');
        } else {
            multiBox.classList.add('hidden');
        }

        // Show panel
        assignmentPanel.classList.remove('hidden');
        setTimeout(() => {
            assignmentPanel.classList.remove('translate-y-10', 'opacity-0', 'scale-95');
        }, 10);

        // Fetch nearby brigades
        brigadesList.innerHTML = '<div class="text-center py-4 text-gray-400"><i class="fa-solid fa-spinner fa-spin"></i></div>';
        
        try {
            const reqBody = {
                latitude: call.latitude || 41.2995,
                longitude: call.longitude || 69.2401,
                radius_km: 50,
                limit: 5
            };
            if (call.service_type_id) {
                reqBody.service_type_id = call.service_type_id;
            }

            const res = await fetch('/api/v1/dispatcher/nearby', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(reqBody)
            });
            
            if (res.ok) {
                const brigades = await res.json();
                brigadesList.innerHTML = '';
                
                if (brigades.length === 0) {
                    brigadesList.innerHTML = '<div class="text-center py-4 text-gray-500">Yaqin atrofda bo\'sh brigada yo\'q</div>';
                    return;
                }
                
                brigades.forEach(b => {
                    const clone = brigadeRowTemplate.content.cloneNode(true);
                    clone.querySelector('.vehicle-num').textContent = b.vehicle_number;
                    if(b.distance_km) {
                        clone.querySelector('.distance').innerHTML = `<i class="fa-solid fa-route text-[10px]"></i> ${(b.distance_km).toFixed(1)} km`;
                    } else {
                        clone.querySelector('.distance').textContent = "Masofa noma'lum";
                    }
                    
                    const btn = clone.querySelector('.assign-btn');
                    btn.addEventListener('click', () => assignBrigade(b.id, btn));
                    
                    brigadesList.appendChild(clone);
                });
            }
        } catch (e) {
            brigadesList.innerHTML = '<div class="text-center text-red-400 py-4">Xatolik</div>';
        }
    };

    window.closeAssignmentPanel = function() {
        assignmentPanel.classList.add('translate-y-10', 'opacity-0', 'scale-95');
        setTimeout(() => {
            assignmentPanel.classList.add('hidden');
        }, 300);
        currentAssignCallId = null;
    };

    async function assignBrigade(brigadeId, btnElement) {
        btnElement.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        btnElement.disabled = true;
        
        try {
            const res = await fetch('/api/v1/dispatcher/assign', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    call_id: currentAssignCallId,
                    brigade_id: brigadeId
                })
            });
            
            if (res.ok) {
                showToast("Muvaffaqiyatli", "Brigada tayinlandi");
                closeAssignmentPanel();
                await loadStats();
            } else {
                showToast("Xatolik", "Tayinlashda xatolik yuz berdi");
                btnElement.innerHTML = 'Tayinlash';
                btnElement.disabled = false;
            }
        } catch(e) {
            btnElement.innerHTML = 'Tayinlash';
            btnElement.disabled = false;
        }
    }

    // WebSocket
    let ws = null;
    function connectWebSocket() {
        if (ws) {
            ws.close(); // Close old connection if filter changed
        }
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let wsUrl = `${protocol}//${window.location.host}/ws/dispatcher?token=${token}`;
        if (activeServiceType) {
            wsUrl = `${protocol}//${window.location.host}/ws/dispatcher/${activeServiceType}?token=${token}`;
        }
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log(`WebSocket connected to ${activeServiceType || 'all'}`);
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'new_sos') {
                showToast("Yangi SOS!", data.call.patient_name || 'Noma\'lum bemor');
                // Play sound
                try {
                    const audio = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
                    audio.play();
                } catch(e){}
                
                calls.unshift(data.call);
                renderCalls();
                loadStats();
            } else if (data.type === 'status_update') {
                const idx = calls.findIndex(c => c.id === data.call_id);
                if (idx !== -1) {
                    calls[idx].status = data.new_status;
                    if (data.new_status === 'completed' || data.new_status === 'cancelled') {
                        calls.splice(idx, 1);
                    }
                    renderCalls();
                    loadStats();
                } else if (data.new_status === 'cancelled') {
                    loadStats();
                }
            }
        };

        ws.onclose = () => {
            setTimeout(connectWebSocket, 5000);
        };
    }

    // Utils
    function getTimeAgo(dateStr) {
        const diff = Math.floor((new Date() - new Date(dateStr)) / 60000);
        if (diff < 1) return 'Hozirgina';
        if (diff < 60) return `${diff} daq oldin`;
        return `${Math.floor(diff/60)} soat oldin`;
    }

    window.showToast = function(title, desc) {
        const toast = document.getElementById('toast');
        document.getElementById('toastTitle').textContent = title;
        document.getElementById('toastDesc').textContent = desc;
        
        toast.classList.remove('translate-y-[150%]', 'opacity-0');
        
        setTimeout(() => {
            hideToast();
        }, 4000);
    }

    window.hideToast = function() {
        document.getElementById('toast').classList.add('translate-y-[150%]', 'opacity-0');
    }

    init();
});
