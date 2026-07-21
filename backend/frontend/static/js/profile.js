/**
 * Tez Yordam EMS - Profile.js
 */

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    const userName = document.getElementById('userName');
    const userRole = document.getElementById('userRole');
    const userPhone = document.getElementById('userPhone');
    const avatarInitials = document.getElementById('avatarInitials');
    
    const inputName = document.getElementById('inputName');
    const inputPhone = document.getElementById('inputPhone');
    const inputAllergies = document.getElementById('inputAllergies');
    const inputChronic = document.getElementById('inputChronic');
    
    const profileForm = document.getElementById('profileForm');
    const medicalForm = document.getElementById('medicalForm');
    const toast = document.getElementById('toast');

    // Load initial data
    async function loadProfile() {
        try {
            const res = await fetch('/api/v1/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                
                userName.textContent = data.full_name;
                userRole.textContent = data.role.toUpperCase();
                userPhone.textContent = data.phone;
                avatarInitials.textContent = data.full_name.charAt(0).toUpperCase();
                
                inputName.value = data.full_name;
                inputPhone.value = data.phone;
                
                if(data.blood_type) {
                    const rb = document.querySelector(`input[name="blood_type"][value="${data.blood_type}"]`);
                    if(rb) rb.checked = true;
                }
                
                if(data.allergies) {
                    inputAllergies.value = data.allergies.join(', ');
                }
                if(data.chronic_conditions) {
                    inputChronic.value = data.chronic_conditions.join(', ');
                }
                
            } else if (res.status === 401) {
                window.location.href = '/login';
            }
        } catch (e) {
            console.error(e);
        }
    }

    profileForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const res = await fetch('/api/v1/auth/profile', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    full_name: inputName.value,
                    phone: inputPhone.value
                })
            });
            if (res.ok) {
                showToast("Asosiy ma'lumotlar saqlandi");
                loadProfile();
            }
        } catch (e) { console.error(e); }
    });

    medicalForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const checkedBlood = document.querySelector('input[name="blood_type"]:checked');
        const allergiesList = inputAllergies.value ? inputAllergies.value.split(',').map(s=>s.trim()).filter(s=>s) : [];
        const chronicList = inputChronic.value ? inputChronic.value.split(',').map(s=>s.trim()).filter(s=>s) : [];
        
        try {
            const res = await fetch('/api/v1/auth/medical-info', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    blood_type: checkedBlood ? checkedBlood.value : null,
                    allergies: allergiesList,
                    chronic_conditions: chronicList
                })
            });
            if (res.ok) {
                showToast("Tibbiy ma'lumotlar saqlandi");
            }
        } catch (e) { console.error(e); }
    });

    function showToast(msg) {
        document.getElementById('toastMsg').textContent = msg;
        toast.classList.remove('translate-y-[200%]');
        setTimeout(() => {
            toast.classList.add('translate-y-[200%]');
        }, 3000);
    }

    window.logout = function() {
        localStorage.removeItem('access_token');
        window.location.href = '/';
    }

    loadProfile();
});
