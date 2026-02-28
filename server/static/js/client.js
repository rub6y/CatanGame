const socket = io();

// Game state variables
let currentUser = null;
let currentRole = null;
let gameStarted = false;
let currentPlayer = null;
let selectedBuilding = null;  // 'settlement', 'road', or null
let hasRolledDice = false;

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
const joinColorPicker = document.getElementById('join-color-picker');
const startGameBtn = document.getElementById('start-game-btn');
const gamePlayersList = document.getElementById('game-players');
const gameObserversList = document.getElementById('game-observers');
const gameConsole = document.getElementById('game-console');
const gameBoard = document.getElementById('game-board');
const nextTurnBtn = document.getElementById('next-turn-btn');
const colorPicker = document.getElementById('color-picker');
const placeSettlementBtn = document.getElementById('place-settlement-btn');
const placeRoadBtn = document.getElementById('place-road-btn');
const rollDiceBtn = document.getElementById('roll-dice-btn');
const diceDisplay = document.getElementById('dice-display');
const resourceDisplay = document.getElementById('resource-display');

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
    const color = joinColorPicker.value;

    currentUser = name;
    currentRole = role;
    socket.emit('join', { name: name, role: role, color: color });
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
    if (!hasRolledDice) {
        alert('You must roll the dice before advancing to the next turn!');
        return;
    }
    socket.emit('next_turn', { name: currentUser });
});

/**
 * Handle Roll Dice button click
 */
rollDiceBtn.addEventListener('click', () => {
    socket.emit('roll_dice', { name: currentUser });
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
            // Use player's color for current turn highlight
            const playerData = currentBoardData?.players?.find(p => p.name === name);
            if (playerData?.color) {
                li.style.backgroundColor = playerData.color;
                li.style.color = getContrastColor(playerData.color);
            }
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
 * Get contrasting text color (black or white) based on background color
 */
function getContrastColor(hexColor) {
    const r = parseInt(hexColor.slice(1, 3), 16);
    const g = parseInt(hexColor.slice(3, 5), 16);
    const b = parseInt(hexColor.slice(5, 7), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5 ? '#2c3e50' : '#ffffff';
}

/**
 * Render resource panel - shows current user's resources
 */
function renderResourcePanel() {
    if (!currentBoardData || !currentBoardData.players) {
        return;
    }
    
    const player = currentBoardData.players.find(p => p.name === currentUser);
    if (!player) {
        return;
    }
    
    const resources = player.resources || {};
    const resourceIcons = {
        wood: '🌲',
        brick: '🧱',
        sheep: '🐑',
        wheat: '🌾',
        ore: '🪨'
    };
    const resourceNames = {
        wood: 'Wood',
        brick: 'Brick',
        sheep: 'Sheep',
        wheat: 'Wheat',
        ore: 'Ore'
    };
    
    let html = '';
    for (const [type, count] of Object.entries(resources)) {
        html += `<div class="resource res-${type}"><span>${resourceIcons[type]} ${resourceNames[type]}</span><span>${count}</span></div>`;
    }
    
    resourceDisplay.innerHTML = html;
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
    hasRolledDice = false;
    userScreen.classList.add('hidden');
    gameScreen.classList.remove('hidden');
    renderGameSidebar(data);
    updateConsoleVisibility();
    
    // Store board data and render
    currentBoardData = data.board;
    if (data.board) {
        window.BoardRenderer.render(data.board, 'board-canvas');
    }
    
    // Set color picker to current user's color
    const currentPlayerData = data.board?.players?.find(p => p.name === currentUser);
    if (currentPlayerData?.color) {
        colorPicker.value = currentPlayerData.color;
    }
    
    // Render resource panel
    renderResourcePanel();
    
    // Enable dice button for the first player
    if (currentPlayer === currentUser) {
        rollDiceBtn.disabled = false;
        rollDiceBtn.textContent = 'Roll Dice';
        diceDisplay.innerHTML = '';
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
        renderResourcePanel();
    }
    
    // Set color picker to current user's color
    const currentPlayerData = data.board?.players?.find(p => p.name === currentUser);
    if (currentPlayerData?.color) {
        colorPicker.value = currentPlayerData.color;
    }
    
    console.log('Reconnected to game. Current player:', data.current_player);
});

socket.on('turn_changed', (data) => {
    currentPlayer = data.current_player;
    renderGameSidebar({ players: data.players, observers: data.observers });
    updateConsoleVisibility();
    renderResourcePanel();
    console.log('Turn changed. Current player:', data.current_player);
    hasRolledDice = false;
    
    // Enable dice button for the current player
    if (currentPlayer === currentUser) {
        rollDiceBtn.disabled = false;
        rollDiceBtn.textContent = 'Roll Dice';
        diceDisplay.innerHTML = '';
    }
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

socket.on('dice_rolled', (data) => {
    console.log(`Player ${data.player} rolled ${data.dice1} + ${data.dice2} = ${data.total}`);
    diceDisplay.innerHTML = `<span class="die">${data.dice1}</span><span class="die">${data.dice2}</span>`;
    rollDiceBtn.disabled = true;
    rollDiceBtn.textContent = `Rolled: ${data.total}`;
    hasRolledDice = true;
    
    // Highlight hexes matching the rolled number
    if (currentBoardData) {
        window.BoardRenderer.render(currentBoardData, 'board-canvas', data.total);
        
        // Clear highlight after 2 seconds
        setTimeout(() => {
            window.BoardRenderer.render(currentBoardData, 'board-canvas', null);
        }, 2000);
    }
});

socket.on('board_updated', (data) => {
    console.log('Board updated');
    currentBoardData = data.board;
    if (data.board) {
        const highlightNumber = data.highlight || null;
        window.BoardRenderer.render(data.board, 'board-canvas', highlightNumber);
    }
    renderResourcePanel();
    
    // Clear highlight after 2 seconds if there was one
    if (data.highlight) {
        setTimeout(() => {
            window.BoardRenderer.render(currentBoardData, 'board-canvas', null);
        }, 2000);
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
