const socket = io();

let currentUser = null;

const joinScreen = document.getElementById('join-screen');
const userScreen = document.getElementById('user-screen');
const usernameInput = document.getElementById('username');
const joinBtn = document.getElementById('join-btn');
const userList = document.getElementById('user-list');

function join() {
    const name = usernameInput.value.trim();
    if (!name) {
        alert('Please enter a name');
        return;
    }

    currentUser = name;
    socket.emit('join', { name: name });
    joinScreen.classList.add('hidden');
    userScreen.classList.remove('hidden');
}

joinBtn.addEventListener('click', join);

usernameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        join();
    }
});

socket.on('user_list', (data) => {
    userList.innerHTML = '';
    data.users.forEach(user => {
        const li = document.createElement('li');
        li.textContent = user;
        if (user === currentUser) {
            li.classList.add('current-user');
        }
        userList.appendChild(li);
    });
});

socket.on('connect', () => {
    if (currentUser) {
        socket.emit('join', { name: currentUser });
    }
});
