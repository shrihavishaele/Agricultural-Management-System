// Toggle functionality for switching between sign-in and sign-up
const container = document.getElementById('container');
const registerBtn = document.getElementById('register');
const loginBtn = document.getElementById('login');

if (registerBtn) {
  registerBtn.addEventListener('click', () => {
    container.classList.add("active");
  });
}

if (loginBtn) {
  loginBtn.addEventListener('click', () => {
    container.classList.remove("active");
  });
}