const socket = io();

// Game state variables
let currentUser = null;
let currentRole = null;
let gameStarted = false;
let currentPlayer = null;
let selectedBuilding = null;  // 'settlement', 'road', or null

// DOM elements
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
const gameBoard = document.getElementById('game-board');
const nextTurnBtn = document.getElementById('next-turn-btn');
const colorPicker = document.getElementById('color-picker');
const placeSettlementBtn = document.getElementById('place-settlement-btn');
const placeRoadBtn = document.getElementById('place-road-btn');

// Store current board data for click handling
let currentBoardData = null;

/**
 * Handle join button click - connect to game
 */
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

/**
 * Handle Start Game button click
 */
startGameBtn.addEventListener('click', () => {
    socket.emit('start_game');
});

/**
 * Handle Next Turn button click
 */
nextTurnBtn.addEventListener('click', () => {
    socket.emit('next_turn', { name: currentUser });
});

/**
 * Handle color picker change - emit set_color event
 */
colorPicker.addEventListener('change', () => {
    socket.emit('set_color', { name: currentUser, color: colorPicker.value });
});

/**
 * Handle Place Settlement button click - toggle settlement placement mode
 */
placeSettlementBtn.addEventListener('click', () => {
    if (selectedBuilding === 'settlement') {
        // Deselect
        selectedBuilding = null;
        placeSettlementBtn.classList.remove('active');
        gameBoard.classList.remove('placement-mode');
    } else {
        // Select settlement
        selectedBuilding = 'settlement';
        placeSettlementBtn.classList.add('active');
        placeRoadBtn.classList.remove('active');
        gameBoard.classList.add('placement-mode');
    }
});

/**
 * Handle Place Road button click - toggle road placement mode
 */
placeRoadBtn.addEventListener('click', () => {
    if (selectedBuilding === 'road') {
        // Deselect
        selectedBuilding = null;
        placeRoadBtn.classList.remove('active');
        gameBoard.classList.remove('placement-mode');
    } else {
        // Select road
        selectedBuilding = 'road';
        placeRoadBtn.classList.add('active');
        placeSettlementBtn.classList.remove('active');
        gameBoard.classList.add('placement-mode');
    }
});

/**
 * Handle canvas click - place building at clicked position
 */
document.getElementById('board-canvas').addEventListener('click', (event) => {
    if (!selectedBuilding || currentUser !== currentPlayer) {
        return;
    }

    const canvas = event.target;
    const rect = canvas.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;

    if (selectedBuilding === 'settlement') {
        // Find nearest vertex
        const vertexKey = window.BoardRenderer.findNearestVertex(clickX, clickY);
        if (vertexKey) {
            console.log('Placing settlement at:', vertexKey);
            socket.emit('place_settlement', { 
                name: currentUser, 
                vertex: vertexKey 
            });
        }
    } else if (selectedBuilding === 'road') {
        // Find nearest edge
        const edgeKey = window.BoardRenderer.findNearestEdge(clickX, clickY);
        if (edgeKey) {
            console.log('Placing road at:', edgeKey);
            socket.emit('place_road', { 
                name: currentUser, 
                edge: edgeKey 
            });
        }
    }
});

/**
 * Update Start Game button visibility based on game state
 */
function updateStartButton() {
    if (currentRole === 'player' && !gameStarted) {
        startGameBtn.classList.remove('hidden');
    } else {
        startGameBtn.classList.add('hidden');
    }
}

/**
 * Render user list in lobby
 */
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

/**
 * Render game sidebar (players and observers)
 */
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

/**
 * Update console visibility and button states based on current turn
 */
function updateConsoleVisibility() {
    if (currentRole === 'observer') {
        gameConsole.classList.add('hidden');
    } else if (currentUser === currentPlayer) {
        gameConsole.classList.remove('hidden');
        nextTurnBtn.disabled = false;
        nextTurnBtn.textContent = `Next Turn`;
        colorPicker.style.display = 'inline-block';
        placeSettlementBtn.style.display = 'inline-block';
        placeRoadBtn.style.display = 'inline-block';
    } else {
        gameConsole.classList.remove('hidden');
        nextTurnBtn.disabled = true;
        nextTurnBtn.textContent = `Waiting for ${currentPlayer}...`;
        colorPicker.style.display = 'inline-block';
        placeSettlementBtn.style.display = 'inline-block';
        placeRoadBtn.style.display = 'inline-block';
    }
    
    // Reset building selection when turn changes
    selectedBuilding = null;
    placeSettlementBtn.classList.remove('active');
    placeRoadBtn.classList.remove('active');
    gameBoard.classList.remove('placement-mode');
}

// Socket event handlers

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
    
    // Store board data and render
    currentBoardData = data.board;
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
    
    // Store board data and render
    currentBoardData = data.board;
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
    // Update player color in currentBoardData before re-rendering
    if (currentBoardData && currentBoardData.players) {
        for (const player of currentBoardData.players) {
            if (player.name === data.name) {
                player.color = data.color;
                break;
            }
        }
    }
    // Re-render board with updated player colors
    if (currentBoardData) {
        window.BoardRenderer.render(currentBoardData, 'board-canvas');
    }
});

socket.on('board_updated', (data) => {
    console.log('Board updated');
    currentBoardData = data.board;
    if (data.board) {
        window.BoardRenderer.render(data.board, 'board-canvas');
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
