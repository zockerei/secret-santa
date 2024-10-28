// Function to view message
function viewMessage(receiverId, year, receiverName) {
    fetch(`/participant/view_message/${receiverId}/${year}`)
        .then(response => response.json())
        .then(data => {
            var modalTitle = document.getElementById("modalTitle");
            var modalMessage = document.getElementById("modalMessage");
            
            modalTitle.textContent = `Nachricht von ${receiverName} (${year})`;
            
            if (data.message) {
                // Wrap the message in a card with the same styling as other messages
                modalMessage.innerHTML = `
                    <div class="card">
                        <div class="card-body">
                            <p class="card-text" style="white-space: pre-wrap;">${data.message}</p>
                        </div>
                    </div>`;
            } else {
                modalMessage.innerHTML = `
                    <div class="card">
                        <div class="card-body">
                            <p class="card-text">Keine Nachricht für diesen Empfänger gefunden.</p>
                        </div>
                    </div>`;
            }
            
            $('#messageModal').modal('show');
        })
        .catch(error => {
            console.error('Fehler:', error);
            alert('Beim Abrufen der Nachricht ist ein Fehler aufgetreten.');
        });
}

// Function to confirm delete
function confirmDelete() {
    const form = document.getElementById('messageForm');
    const actionInput = document.createElement('input');
    actionInput.type = 'hidden';
    actionInput.name = 'action';
    actionInput.value = 'delete';
    form.appendChild(actionInput);
    form.submit();
}
