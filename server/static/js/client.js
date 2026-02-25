const socket = io();

let currentUser = null;
let currentRole = null;
let gameStarted = false;

const joinScreen = document.getElementById('join-screen');
const userScreen = document.getElementById('user-screen');
const usernameInput = document.getElementById('username');
const joinBtn = document.getElementById('join-btn');
const playerList = document.getElementById('players');
const observerList = document.getElementById('observers');
const playerCount = document.getElementById('player-count');
const rolePlayer = document.getElementById('role-player');
const roleObserver = document.getElementById('role-observer');
const startGameBtn = document.getElementById('start-game-btn');

function join() {
    const name = usernameInput.value.trim();
    if (!name) {
        alert('Please enter a name');
        return;
    }

    const role = document.querySelector('input[name="role"]:checked').value;

    currentUser = name;
    currentRole = role;
    socket.emit('join', { name: name, role: role });
    joinScreen.classList.add('hidden');
    userScreen.classList.remove('hidden');
    updateStartButton();
}

joinBtn.addEventListener('click', join);

usernameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        join();
    }
});

startGameBtn.addEventListener('click', () => {
    socket.emit('start_game');
});

function updateStartButton() {
    if (currentRole === 'player' && !gameStarted) {
        startGameBtn.classList.remove('hidden');
    } else {
        startGameBtn.classList.add('hidden');
    }
}

function renderUserList(data) {
    playerList.innerHTML = '';
    observerList.innerHTML = '';
    playerCount.textContent = data.players.length;

    data.players.forEach(user => {
        const li = document.createElement('li');
        li.textContent = user.name;
        if (user.name === currentUser) {
            li.classList.add('current-user');
        }
        playerList.appendChild(li);
    });

    data.observers.forEach(user => {
        const li = document.createElement('li');
        li.textContent = user.name;
        if (user.name === currentUser) {
            li.classList.add('current-user');
        }
        observerList.appendChild(li);
    });
}

socket.on('user_list', (data) => {
    renderUserList(data);
    updateStartButton();
});

socket.on('game_started', (data) => {
    gameStarted = true;
    startGameBtn.classList.add('hidden');
    console.log('Game started! Player order:', data.players);
    console.log('Current player:', data.current_player);
});

socket.on('error', (data) => {
    alert(data.message);
});

socket.on('connect', () => {
    if (currentUser) {
        socket.emit('join', { name: currentUser, role: currentRole });
    }
});
