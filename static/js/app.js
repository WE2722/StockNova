document.body.addEventListener('htmx:afterSwap', () => {
  const toasts = document.querySelectorAll('.toast');
  toasts.forEach((toastEl) => {
    const toast = new bootstrap.Toast(toastEl, { delay: 2500 });
    toast.show();
  });
});
