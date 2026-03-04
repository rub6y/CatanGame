const socket = io();

// Game state variables
let currentUser = null;
let currentRole = null;
let gameStarted = false;
let currentPlayer = null;
let selectedBuilding = null;  // 'settlement', 'road', or null
let hasRolledDice = false;

// DOM elements
const gameTitle = document.getElementById('game-title');

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
const bankDisplay = document.getElementById('bank-display');
const tradePanel = document.getElementById('trade-panel');
const proposeTradeBtn = document.getElementById('propose-trade-btn');
const tradeOffersDiv = document.getElementById('trade-offers');
const myOffersDiv = document.getElementById('my-offers');
const tradeModal = document.getElementById('trade-modal');
const closeTradeModal = document.getElementById('close-trade-modal');
const submitTradeBtn = document.getElementById('submit-trade-btn');

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
        
        // Color each player with their own color
        const playerData = currentBoardData?.players?.find(p => p.name === name);
        if (playerData?.color) {
            li.style.backgroundColor = playerData.color;
            li.style.color = getContrastColor(playerData.color);
        }
        
        // Highlight current player with border
        if (name === currentPlayer) {
            li.classList.add('current-turn');
            li.style.border = '3px solid white';
            li.style.boxShadow = '0 0 10px rgba(255,255,255,0.5)';
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
        html += `<div class="resource res-${type}">${resourceIcons[type]}${count}</div>`;
    }
    
    resourceDisplay.innerHTML = html;
}

/**
 * Render bank panel - shows bank resources as percentage
 */
function renderBank() {
    if (!currentBoardData || !currentBoardData.bank) {
        return;
    }
    
    const bank = currentBoardData.bank;
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
    
    const RESOURCE_LIMIT = 19;
    
    let html = '';
    for (const [type, count] of Object.entries(bank)) {
        const percentage = Math.round((count / RESOURCE_LIMIT) * 100 / 25) * 25;
        html += `<div class="bank-resource bank-${type}">${resourceIcons[type]}${percentage}%</div>`;
    }
    
    bankDisplay.innerHTML = html;
}

/**
 * Render trade offers panel
 */
function renderTradeOffers() {
    if (!currentBoardData || !currentBoardData.trades) {
        tradeOffersDiv.innerHTML = '';
        myOffersDiv.innerHTML = '';
        return;
    }
    
    const activeTrades = currentBoardData.trades.active || [];
    const myOffers = currentBoardData.trades.my_offers || {};
    
    const resourceIcons = {
        wood: '🌲',
        brick: '🧱',
        sheep: '🐑',
        wheat: '🌾',
        ore: '🪨'
    };
    
    // Render active offers (other players' offers - responder view)
    let offersHtml = '';
    const otherOffers = activeTrades.filter(t => t.proposer !== currentUser);
    
    if (otherOffers.length > 0) {
        offersHtml = '<h4>Active Offers:</h4>';
        for (const offer of otherOffers) {
            const accepted = offer.accepted_by || {};
            const hasAcceptedMe = accepted[currentUser] === true;
            
            // For responder: give = what proposer wants, get = what proposer offers
            let giveStr = '';
            for (const [res, count] of Object.entries(offer.wanted_resources)) {
                if (count > 0) giveStr += `${count}${resourceIcons[res]} `;
            }
            
            let wantStr = '';
            for (const [res, count] of Object.entries(offer.offered_resources)) {
                if (count > 0) wantStr += `${count}${resourceIcons[res]} `;
            }
            
            // Get player colors
            const proposerPlayer = currentBoardData.players?.find(p => p.name === offer.proposer);
            const proposerColor = proposerPlayer?.color || '#e74c3c';
            
            // Show Accept and Deny buttons for responders
            const acceptBtnColor = hasAcceptedMe ? '#27ae60' : '#95a5a6';
            const acceptBtnText = hasAcceptedMe ? 'Accepted' : 'Accept';
            
            offersHtml += `
                <div class="trade-offer" data-offer-id="${offer.id}" data-created="${offer.created_at}">
                    <div class="trade-offer-header">
                        <span class="trade-offer-player" style="color: ${proposerColor}">${offer.proposer}</span>
                        <span class="trade-timer" data-offer-id="${offer.id}"></span>
                    </div>
                    <div class="trade-offer-resources">
                        <span class="give">You give: ${giveStr}</span>
                        <span>→</span>
                        <span class="want">You get: ${wantStr}</span>
                    </div>
                    <div class="trade-offer-actions" style="display: flex; flex-wrap: nowrap; gap: 5px; justify-content: center;">
                        <button class="accept-btn" style="background-color: ${acceptBtnColor}; font-size: 11px; padding: 4px 8px;" onclick="acceptTrade(${offer.id})">${acceptBtnText}</button>
                        <button class="decline-btn" style="font-size: 11px; padding: 4px 8px;" onclick="declineTrade(${offer.id})">Deny</button>
                    </div>
                </div>
            `;
        }
    }
    tradeOffersDiv.innerHTML = offersHtml;
    
    // Render my offers (own offers - proposer view)
    let myOffersHtml = '';
    const myOfferList = currentBoardData.trades?.my_offers?.[currentUser] || [];
    
    if (myOfferList.length > 0) {
        myOffersHtml = '<h4>Your Offers:</h4>';
        for (const offer of myOfferList) {
            const accepted = offer.accepted_by || {};
            
            let giveStr = '';
            for (const [res, count] of Object.entries(offer.offered_resources)) {
                if (count > 0) giveStr += `${count}${resourceIcons[res]} `;
            }
            
            let wantStr = '';
            for (const [res, count] of Object.entries(offer.wanted_resources)) {
                if (count > 0) wantStr += `${count}${resourceIcons[res]} `;
            }
            
            // Show 3 buttons for each player - grey if not accepted, colored if accepted
            let buttonsHtml = '<div class="trade-offer-actions" style="display: flex; flex-wrap: nowrap; gap: 5px; justify-content: center;">';
            const allPlayers = currentBoardData.players || [];
            for (const player of allPlayers) {
                if (player.name === currentUser) continue;
                const hasAccepted = accepted[player.name] === true;
                const btnColor = hasAccepted ? (player.color || '#27ae60') : '#7f8c8d';
                const btnText = hasAccepted ? player.name : player.name;
                buttonsHtml += `<button class="accepted-player" style="background-color: ${btnColor}; font-size: 11px; padding: 4px 8px;" onclick="completeTrade(${offer.id}, '${player.name}')">${btnText}</button>`;
            }
            buttonsHtml += '</div>';
            
            myOffersHtml += `
                <div class="trade-offer" data-offer-id="${offer.id}" data-created="${offer.created_at}">
                    <div class="trade-offer-header">
                        <span class="trade-timer" data-offer-id="${offer.id}"></span>
                    </div>
                    <div class="trade-offer-resources">
                        <span class="give">${giveStr}</span>
                        <span>→</span>
                        <span class="want">${wantStr}</span>
                    </div>
                    ${buttonsHtml}
                </div>
            `;
        }
    }
    myOffersDiv.innerHTML = myOffersHtml;
}

/**
 * Update trade offer timers
 */
function updateTradeTimers() {
    const timers = document.querySelectorAll('.trade-timer');
    const currentTime = Date.now() / 1000;
    let needsRefresh = false;
    
    timers.forEach(timer => {
        const offerId = timer.dataset.offerId;
        const offerEl = timer.closest('.trade-offer');
        if (!offerEl) return;
        
        const createdAt = parseFloat(offerEl.dataset.created);
        if (isNaN(createdAt)) return;
        
        const elapsed = currentTime - createdAt;
        const remaining = Math.max(0, 10 - Math.floor(elapsed));
        
        timer.textContent = `${remaining}s`;
        
        if (remaining === 0) {
            needsRefresh = true;
        }
    });
    
    // Refresh board if any offer expired
    if (needsRefresh && currentBoardData) {
        socket.emit('refresh_board');
    }
}

// Update timers every second
setInterval(updateTradeTimers, 1000);

/**
 * Show trade modal
 */
function showTradeModal() {
    if (!currentUser || currentUser !== currentPlayer) {
        alert('You can only propose trades on your turn');
        return;
    }
    tradeModal.classList.remove('hidden');
    tradeModal.classList.add('show');
}

/**
 * Hide trade modal
 */
function hideTradeModal() {
    tradeModal.classList.remove('show');
    tradeModal.classList.add('hidden');
    // Reset inputs
    ['wood', 'brick', 'sheep', 'wheat', 'ore'].forEach(res => {
        document.getElementById(`give-${res}`).value = 0;
        document.getElementById(`want-${res}`).value = 0;
    });
}

/**
 * Submit trade proposal
 */
function submitTrade() {
    const offered = {};
    const wanted = {};
    
    ['wood', 'brick', 'sheep', 'wheat', 'ore'].forEach(res => {
        const giveCount = parseInt(document.getElementById(`give-${res}`).value) || 0;
        const wantCount = parseInt(document.getElementById(`want-${res}`).value) || 0;
        if (giveCount > 0) offered[res] = giveCount;
        if (wantCount > 0) wanted[res] = wantCount;
    });
    
    if (Object.keys(offered).length === 0 || Object.keys(wanted).length === 0) {
        alert('Please specify resources to give and want');
        return;
    }
    
    socket.emit('propose_trade', {
        name: currentUser,
        offered: offered,
        wanted: wanted
    });
    
    hideTradeModal();
}

/**
 * Accept a trade offer
 */
function acceptTrade(offerId) {
    socket.emit('accept_trade', {
        name: currentUser,
        offer_id: offerId
    });
}

/**
 * Decline a trade offer
 */
function declineTrade(offerId) {
    socket.emit('decline_trade', {
        name: currentUser,
        offer_id: offerId
    });
}

/**
 * Cancel your trade offer
 */
function cancelTrade(offerId) {
    socket.emit('cancel_trade', {
        name: currentUser,
        offer_id: offerId
    });
}

/**
 * Complete trade with selected player
 */
function completeTrade(offerId, responder) {
    socket.emit('complete_trade', {
        name: currentUser,
        offer_id: offerId,
        selected_responder: responder
    });
}

// Trade modal event listeners
if (proposeTradeBtn) proposeTradeBtn.addEventListener('click', showTradeModal);
if (closeTradeModal) closeTradeModal.addEventListener('click', hideTradeModal);
if (submitTradeBtn) submitTradeBtn.addEventListener('click', submitTrade);
if (tradeModal) tradeModal.addEventListener('click', (e) => {
    if (e.target === tradeModal) hideTradeModal();
});

/**
 * Update console visibility and button states based on current turn
 */
function updateConsoleVisibility() {
    // Update button colors based on current player
    updateButtonColors();
    
    // Show/hide trade button based on turn
    if (currentRole !== 'observer' && currentUser === currentPlayer) {
        proposeTradeBtn.style.display = 'inline-block';
    } else {
        proposeTradeBtn.style.display = 'none';
    }
    
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

/**
 * Update button colors and title based on current user
 */
function updateButtonColors() {
    const buttons = [rollDiceBtn, placeSettlementBtn, placeRoadBtn, nextTurnBtn];
    const currentUserData = currentBoardData?.players?.find(p => p.name === currentUser);
    const playerColor = currentUserData?.color || '#e67e22';
    const textColor = getContrastColor(playerColor);
    
    buttons.forEach(btn => {
        btn.style.backgroundColor = playerColor;
        btn.style.color = textColor;
    });
    
    // Update title color
    if (gameTitle) {
        gameTitle.style.color = playerColor;
    }
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
    
    // Store board data first so renderGameSidebar can access player colors
    currentBoardData = data.board;
    if (data.board) {
        window.BoardRenderer.render(data.board, 'board-canvas');
    }
    
    renderGameSidebar(data);
    updateConsoleVisibility();
    
    // Set color picker to current user's color
    const currentPlayerData = data.board?.players?.find(p => p.name === currentUser);
    if (currentPlayerData?.color) {
        colorPicker.value = currentPlayerData.color;
    }
    
    // Render resource panel
    renderResourcePanel();
    
    // Render bank
    renderBank();
    
    // Update button colors
    updateButtonColors();
    
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
        renderBank();
    }
    
    // Set color picker to current user's color
    const currentPlayerData = data.board?.players?.find(p => p.name === currentUser);
    if (currentPlayerData?.color) {
        colorPicker.value = currentPlayerData.color;
    }
    
    // Update button colors
    updateButtonColors();
    
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
    // Update buttons and sidebar with new color
    updateButtonColors();
    if (currentPlayer) {
        renderGameSidebar({ players: currentBoardData?.players?.map(p => p.name) || [], observers: [] });
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
    renderBank();
    renderTradeOffers();
    
    // Clear highlight after 2 seconds if there was one
    if (data.highlight) {
        setTimeout(() => {
            window.BoardRenderer.render(currentBoardData, 'board-canvas', null);
        }, 2000);
    }
});

socket.on('trade_proposed', (data) => {
    console.log('Trade proposed:', data.offer);
    if (currentBoardData && currentBoardData.trades) {
        currentBoardData.trades.active.push(data.offer);
    }
    renderTradeOffers();
});

socket.on('trade_accepted', (data) => {
    console.log('Trade accepted:', data);
    renderTradeOffers();
});

socket.on('trade_declined', (data) => {
    console.log('Trade declined:', data);
    renderTradeOffers();
});

socket.on('trade_cancelled', (data) => {
    console.log('Trade cancelled:', data);
    renderTradeOffers();
});

socket.on('trade_completed', (data) => {
    console.log('Trade completed:', data);
    renderTradeOffers();
});

socket.on('error', (data) => {
    alert(data.message);
});

socket.on('connect', () => {
    if (currentUser) {
        socket.emit('join', { name: currentUser, role: currentRole });
    }
});
