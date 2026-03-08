const checkBtn = document.getElementById('check-update-btn');
const backBtn = document.getElementById('back-btn');
const statusMessage = document.getElementById('status-message');

checkBtn.addEventListener('click', () => {
    statusMessage.textContent = 'Buscando...';
    window.updater.checkForUpdate();
});

if (backBtn) {
    backBtn.addEventListener('click', () => {
        window.location.href = 'http://localhost:23333';
    });
}

window.updater.onUpdateMessage((message) => {
    statusMessage.textContent = message;
});