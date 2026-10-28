const opinionView = document.getElementById('opinion-view');
if (opinionView) {
  opinionView.addEventListener('change', () => opinionView.form.requestSubmit());
}
