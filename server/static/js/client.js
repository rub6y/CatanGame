const socket = io();

let currentUser = null;
let currentRole = null;
let gameStarted = false;
let currentPlayer = null;

const joinScreen = document.getElementById('join-screen');
const userScreen = document.getElementById('user-screen');
const gameScreen = document.getElementById('game-screen');
const usernameInput = document.getElementById('username');
const joinBtn = document.getElementById('join-btn');
const playerList = document.getElementById('players');
const observerList = document.getElementById('observers');
const playerCount = document.getElementById('player-count');
const rolePlayer = document.getElementById('role-player');
const roleObserver = document.getElementById('role-observer');
const startGameBtn = document.getElementById('start-game-btn');
const gamePlayersList = document.getElementById('game-players');
const gameObserversList = document.getElementById('game-observers');
const gameConsole = document.getElementById('game-console');
const nextTurnBtn = document.getElementById('next-turn-btn');
const colorPicker = document.getElementById('color-picker');

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

nextTurnBtn.addEventListener('click', () => {
    socket.emit('next_turn', { name: currentUser });
});

colorPicker.addEventListener('change', () => {
    socket.emit('set_color', { name: currentUser, color: colorPicker.value });
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

function renderGameSidebar(data) {
    gamePlayersList.innerHTML = '';
    gameObserversList.innerHTML = '';

    data.players.forEach(name => {
        const li = document.createElement('li');
        li.textContent = name;
        if (name === currentPlayer) {
            li.classList.add('current-turn');
        }
        gamePlayersList.appendChild(li);
    });

    data.observers.forEach(name => {
        const li = document.createElement('li');
        li.textContent = name;
        gameObserversList.appendChild(li);
    });
}

function updateConsoleVisibility() {
    if (currentRole === 'observer') {
        gameConsole.classList.add('hidden');
    } else if (currentUser === currentPlayer) {
        gameConsole.classList.remove('hidden');
        nextTurnBtn.disabled = false;
        nextTurnBtn.textContent = `Next Turn`;
        colorPicker.style.display = 'inline-block';
    } else {
        gameConsole.classList.remove('hidden');
        nextTurnBtn.disabled = true;
        nextTurnBtn.textContent = `Waiting for ${currentPlayer}...`;
        colorPicker.style.display = 'inline-block';
    }
}

socket.on('user_list', (data) => {
    renderUserList(data);
    updateStartButton();
});

socket.on('game_started', (data) => {
    gameStarted = true;
    currentPlayer = data.current_player;
    currentRole = 'player';
    userScreen.classList.add('hidden');
    gameScreen.classList.remove('hidden');
    renderGameSidebar(data);
    updateConsoleVisibility();
    
    if (data.board) {
        window.BoardRenderer.render(data.board, 'board-canvas');
    }
    
    console.log('Game started! Player order:', data.players);
    console.log('Current player:', data.current_player);
});

socket.on('game_state', (data) => {
    gameStarted = true;
    currentPlayer = data.current_player;
    if (data.players.includes(currentUser)) {
        currentRole = 'player';
    } else {
        currentRole = 'observer';
    }
    userScreen.classList.add('hidden');
    gameScreen.classList.remove('hidden');
    renderGameSidebar(data);
    updateConsoleVisibility();
    
    if (data.board) {
        window.BoardRenderer.render(data.board, 'board-canvas');
    }
    
    console.log('Reconnected to game. Current player:', data.current_player);
});

socket.on('turn_changed', (data) => {
    currentPlayer = data.current_player;
    renderGameSidebar({ players: data.players, observers: data.observers });
    updateConsoleVisibility();
    console.log('Turn changed. Current player:', data.current_player);
});

socket.on('player_color_changed', (data) => {
    console.log(`Player ${data.name} changed color to ${data.color}`);
    if (data.name === currentUser) {
        colorPicker.value = data.color;
    }
});

socket.on('error', (data) => {
    alert(data.message);
});

socket.on('connect', () => {
    if (currentUser) {
        socket.emit('join', { name: currentUser, role: currentRole });
    }
});
