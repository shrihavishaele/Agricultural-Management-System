// Original toggle functionality
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

// Login functionality
document.addEventListener('DOMContentLoaded', function() {
  const loginForm = document.querySelector('.sign-in form');
  
  if (loginForm) {
    loginForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      const email = loginForm.querySelector('input[type="email"]').value;
      const password = loginForm.querySelector('input[type="password"]').value;
      
      // In a real application, you would validate credentials against a database
      // For this example, we'll just store the email and redirect
      if (email && password) {
        // Store email in localStorage
        localStorage.setItem('userEmail', email);
        
        // Fetch user data from backend
        fetch('http://localhost:5000/user', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email: email }),
        })
        .then(response => response.json())
        .then(data => {
          if (data.username) {
            // Store username in localStorage
            localStorage.setItem('username', data.username);
          } else {
            // If no username found, use email as fallback
            const emailUsername = email.split('@')[0];
            localStorage.setItem('username', emailUsername);
          }
          // Redirect to role page regardless of backend response
          window.location.href = 'role.html';
        })
        .catch(error => {
          console.error('Error:', error);
          // Even if backend fails, still redirect but use email as username
          const emailUsername = email.split('@')[0];
          localStorage.setItem('username', emailUsername);
          window.location.href = 'role.html';
        });
      } else {
        alert('Please enter both email and password');
      }
    });
  }
});