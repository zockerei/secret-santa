// Add a simple snowfall effect
function createSnowflakes() {
    const snowflakeContainer = document.querySelector('.snowflake');
    for (let i = 0; i < 100; i++) {
        const snowflake = document.createElement('div');
        snowflake.className = 'snowflake-item';
        snowflake.style.left = Math.random() * 100 + 'vw';
        snowflake.style.animationDuration = Math.random() * 3 + 2 + 's';
        snowflakeContainer.appendChild(snowflake);
    }
}

// Call the function when the page loads
window.onload = function() {
    playChristmasMusic();
    createSnowflakes(); // Initialize snowflakes
};

// Optionally, add a toggle for the music
document.getElementById('music-toggle').addEventListener('click', function() {
    const audio = document.querySelector('audio');
    if (audio.paused) {
        audio.play();
    } else {
        audio.pause();
    }
});

// Function to view message
function viewMessage(receiverId, year, receiverName) {
    fetch(`/participant/view_message/${receiverId}/${year}`)
        .then(response => response.json())
        .then(data => {
            var modalTitle = document.getElementById("modalTitle");
            var modalMessage = document.getElementById("modalMessage");
            
            modalTitle.textContent = `Nachricht von ${receiverName} (${year})`;
            
            if (data.message) {
                modalMessage.textContent = data.message;
            } else {
                modalMessage.textContent = 'Keine Nachricht für diesen Empfänger gefunden.';
            }
            
            $('#messageModal').modal('show');
        })
        .catch(error => {
            console.error('Fehler:', error);
            alert('Beim Abrufen der Nachricht ist ein Fehler aufgetreten.');
        });
}

// Function to confirm delete
function confirmDelete(messageId) {
    var deleteForm = document.getElementById('deleteForm');
    var baseUrl = "{{ url_for('participant.delete_message', message_id=0) }}";
    deleteForm.action = baseUrl.replace('0', messageId);
    $('#deleteModal').modal('show');
}

// Add this to your script.js
console.log("JavaScript file is loaded!");
