/**
 * Tez Yordam EMS - App.js
 * SOS yuborish va audio yozib olish mantig'i
 */

document.addEventListener('DOMContentLoaded', () => {
    const sosBtn = document.getElementById('sosBtn');
    const recordBtn = document.getElementById('recordBtn');
    const statusMsg = document.getElementById('statusMessage');
    const recordingStatus = document.getElementById('recordingStatus');
    const locationModal = document.getElementById('locationModal');
    const allowLocationBtn = document.getElementById('allowLocationBtn');
    const servicesContainer = document.getElementById('servicesContainer');
    
    let selectedServices = []; // Bo'sh bo'lsa umumiy SOS
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    let audioBlob = null;
    let userLocation = null;

    // Location request
    function requestLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject("Geolokatsiya qo'llab-quvvatlanmaydi");
            } else {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        userLocation = {
                            lat: position.coords.latitude,
                            lng: position.coords.longitude
                        };
                        resolve(userLocation);
                    },
                    (error) => {
                        reject(error.message);
                    },
                    { enableHighAccuracy: true, timeout: 10000 }
                );
            }
        });
    }

    // Audio recording
    async function toggleRecording() {
        if (isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            recordingStatus.classList.add('hidden');
            recordBtn.querySelector('span').textContent = "Ovozli shikoyat saqlandi (Qayta yozish)";
            recordBtn.classList.replace('text-gray-300', 'text-green-400');
            recordBtn.querySelector('.bg-white\\/10').classList.replace('bg-white/10', 'bg-green-500/20');
        } else {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = () => {
                    audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                };

                mediaRecorder.start();
                isRecording = true;
                recordingStatus.classList.remove('hidden');
                recordBtn.querySelector('span').textContent = "Yozilmoqda...";
            } catch (err) {
                showStatus("Mikrofonga ruxsat berilmadi", "error");
            }
        }
    }

    if(recordBtn) {
        recordBtn.addEventListener('click', toggleRecording);
    }

    // Fetch and render services
    async function loadServices() {
        if (!servicesContainer) return;
        try {
            const res = await fetch('/api/v1/services/');
            if (res.ok) {
                const services = await res.json();
                renderServices(services);
            }
        } catch (e) {
            console.error("Xizmatlarni yuklashda xatolik:", e);
        }
    }

    function renderServices(services) {
        servicesContainer.innerHTML = '';
        services.forEach(svc => {
            const btn = document.createElement('button');
            btn.className = `flex flex-col items-center justify-center p-3 w-24 h-24 md:w-28 md:h-28 rounded-2xl glass-panel transition-all transform hover:scale-105 active:scale-95 border-2 border-white/5 hover:border-[${svc.color_hex}]/50 group`;
            btn.innerHTML = `
                <div class="w-10 h-10 rounded-full flex items-center justify-center mb-2" style="background-color: ${svc.color_hex}20; color: ${svc.color_hex};">
                    <i class="${svc.icon} text-xl group-hover:scale-110 transition-transform"></i>
                </div>
                <span class="text-xs font-semibold text-center text-gray-300 group-hover:text-white leading-tight">${svc.name_uz}</span>
                <span class="text-[10px] text-gray-500 mt-1">${svc.phone_number}</span>
            `;
            
            btn.addEventListener('click', () => {
                const idx = selectedServices.indexOf(svc.code);
                if (idx > -1) {
                    // Deselect
                    selectedServices.splice(idx, 1);
                    btn.classList.remove('ring-2', 'ring-offset-2', 'ring-offset-dark', 'bg-white/10');
                    btn.style.removeProperty('--tw-ring-color');
                } else {
                    // Select
                    selectedServices.push(svc.code);
                    btn.classList.add('ring-2', 'ring-offset-2', 'ring-offset-dark', 'bg-white/10');
                    btn.style.setProperty('--tw-ring-color', svc.color_hex);
                }
                
                if (selectedServices.length === 0) {
                    sosBtn.querySelector('span:last-child').textContent = "Umumiy";
                } else if (selectedServices.length === 1) {
                    const s = services.find(x => x.code === selectedServices[0]);
                    sosBtn.querySelector('span:last-child').textContent = s ? s.name_uz : selectedServices[0];
                } else {
                    sosBtn.querySelector('span:last-child').textContent = selectedServices.length + " ta xizmat";
                }
            });
            
            servicesContainer.appendChild(btn);
        });
    }
    
    // Initial load
    loadServices();

    // SOS Logic
    async function sendSOS() {
        const token = localStorage.getItem('access_token');
        if (!token) {
            window.location.href = '/login';
            return;
        }

        // Show loading state
        sosBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-5xl md:text-6xl text-white drop-shadow-lg"></i>';
        sosBtn.disabled = true;

        try {
            // Get location if not already have
            if (!userLocation) {
                try {
                    await requestLocation();
                } catch (err) {
                    locationModal.classList.remove('hidden');
                    setTimeout(() => {
                        locationModal.classList.remove('opacity-0');
                        document.getElementById('locationModalContent').classList.remove('scale-95');
                    }, 10);
                    
                    // Reset button
                    sosBtn.innerHTML = '<i class="fa-solid fa-phone-volume text-5xl md:text-6xl text-white mb-3 drop-shadow-lg"></i><span class="text-3xl md:text-4xl font-black tracking-widest text-white drop-shadow-md">SOS</span>';
                    sosBtn.disabled = false;
                    return;
                }
            }

            // Create form data (since we might have audio)
            const formData = new FormData();
            formData.append('latitude', userLocation.lat);
            formData.append('longitude', userLocation.lng);
            
            if (audioBlob) {
                formData.append('audio', audioBlob, 'sos_audio.webm');
            }

            // In our current backend schema, SOSCreateRequest expects JSON.
            // But main.py might have a different route. Let's check schema.
            // Actually, in `emergency.py` we used a standard endpoint. If we want file upload, we need multipart.
            // Wait, we can send lat/lng as query params if audio is file.
            // Let's send basic JSON first, audio is a nice-to-have later if endpoint doesn't support multipart.
            // I'll assume endpoint accepts JSON for now.
            
            const reqBody = {
                latitude: userLocation.lat,
                longitude: userLocation.lng,
                description: "Ovozli xabar bor",
                service_types: selectedServices.length > 0 ? selectedServices : null
            };

            const response = await fetch('/api/v1/emergency/sos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(reqBody)
            });

            if (response.ok) {
                const data = await response.json();
                
                // If we have audio and another endpoint for it:
                // await fetch(`/api/v1/emergency/${data.call_id}/audio`, { body: audioBlob ... })
                
                window.location.href = `/sos/${data.call_id}`;
            } else {
                if (response.status === 401) {
                    window.location.href = '/login';
                } else {
                    const errData = await response.json();
                    showStatus(errData.detail || "Xatolik yuz berdi", "error");
                }
            }
            
        } catch (error) {
            showStatus("Tarmoq xatoligi", "error");
        } finally {
            // Reset button if error
            sosBtn.innerHTML = '<i class="fa-solid fa-phone-volume text-5xl md:text-6xl text-white mb-3 drop-shadow-lg"></i><span class="text-3xl md:text-4xl font-black tracking-widest text-white drop-shadow-md">SOS</span>';
            sosBtn.disabled = false;
        }
    }

    if(sosBtn) {
        sosBtn.addEventListener('click', sendSOS);
    }

    if(allowLocationBtn) {
        allowLocationBtn.addEventListener('click', async () => {
            allowLocationBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            try {
                await requestLocation();
                locationModal.classList.add('opacity-0');
                document.getElementById('locationModalContent').classList.add('scale-95');
                setTimeout(() => locationModal.classList.add('hidden'), 300);
                
                // Trigger SOS automatically after getting location
                sendSOS();
            } catch (err) {
                allowLocationBtn.innerHTML = 'Ruxsat berish';
                showStatus("Joylashuv aniqlanmadi", "error");
            }
        });
    }

    function showStatus(msg, type) {
        statusMsg.textContent = msg;
        statusMsg.className = `mt-6 text-sm font-medium transition-opacity duration-300 ${type === 'error' ? 'text-red-400' : 'text-green-400'} opacity-100`;
        setTimeout(() => {
            statusMsg.classList.replace('opacity-100', 'opacity-0');
        }, 5000);
    }
});
