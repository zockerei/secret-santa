document.querySelectorAll('.delete-participant-form').forEach(form => {
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const participantName = this.closest('li').textContent.trim().split('\n')[0];
        
        Swal.fire({
            title: 'Are you sure?',
            text: `Do you want to remove ${participantName}?`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Yes, remove',
            cancelButtonText: 'Cancel'
        }).then((result) => {
            if (result.isConfirmed) {
                this.submit();
            }
        });
    });
});