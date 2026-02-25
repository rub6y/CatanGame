/**
 * Catan Board Renderer
 * Renders the Catan board using HTML5 Canvas
 */

const BOARD_CONFIG = {
    hexRadius: 35,
    edgeRadius: 3,
    colors: {
        ocean: '#1a5276',
        desert: '#f4d03f',
        ore: '#7f8c8d',
        wheat: '#f39c12',
        sheep: '#27ae60',
        brick: '#c0392b',
        wood: '#8b4513',
        highlight: 'rgba(231, 76, 60, 0.5)',
        border: '#2c3e50',
        text: '#ecf0f1',
        numberCircle: '#ecf0f1',
        numberText: '#2c3e50'
    }
};

function cubeToPixel(x, y, z, radius) {
    const px = radius * Math.sqrt(3) * (x / 3 + z / 6);
    const py = radius * 3/2 * (z / 3);
    return { x: px, y: py };
}

function parseKey(key) {
    const parts = key.split(',').map(Number);
    return { x: parts[0], y: parts[1], z: parts[2] };
}

function drawHex(ctx, centerX, centerY, radius, color, number, isLand) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
        const angle = Math.PI / 3 * i - Math.PI / 6;
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.closePath();
    
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = BOARD_CONFIG.colors.border;
    ctx.lineWidth = 2;
    ctx.stroke();
    
    if (isLand && number !== null && number !== undefined) {
        drawNumberToken(ctx, centerX, centerY, number);
    }
}

function drawNumberToken(ctx, centerX, centerY, number) {
    const tokenRadius = 12;
    
    ctx.beginPath();
    ctx.arc(centerX, centerY, tokenRadius, 0, Math.PI * 2);
    ctx.fillStyle = BOARD_CONFIG.colors.numberCircle;
    ctx.fill();
    ctx.strokeStyle = BOARD_CONFIG.colors.border;
    ctx.lineWidth = 1;
    ctx.stroke();
    
    ctx.font = 'bold 14px Arial';
    ctx.fillStyle = BOARD_CONFIG.colors.numberText;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(number.toString(), centerX, centerY);
}

function getHexColor(hexType) {
    return BOARD_CONFIG.colors[hexType] || BOARD_CONFIG.colors.ocean;
}

function drawVertex(ctx, x, y) {
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = 'red';
    ctx.fill();
}

function drawEdge(ctx, x1, y1, x2, y2) {
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = 'red';
    ctx.lineWidth = 3;
    ctx.stroke();
}

function renderBoard(boardData, canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error('Canvas not found:', canvasId);
        return;
    }
    
    const ctx = canvas.getContext('2d');
    const hexes = boardData.hexes;
    
    const hexRadius = BOARD_CONFIG.hexRadius;
    
    const hexKeys = Object.keys(hexes);
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    
    const hexPositions = {};
    for (const key of hexKeys) {
        const coords = parseKey(key);
        const pos = cubeToPixel(coords.x, coords.y, coords.z, hexRadius);
        hexPositions[key] = pos;
        
        minX = Math.min(minX, pos.x - hexRadius);
        maxX = Math.max(maxX, pos.x + hexRadius);
        minY = Math.min(minY, pos.y - hexRadius);
        maxY = Math.max(maxY, pos.y + hexRadius);
    }
    
    const padding = hexRadius + 20;
    const width = maxX - minX + padding * 2;
    const height = maxY - minY + padding * 2;
    
    canvas.width = width;
    canvas.height = height;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    ctx.translate(-minX + padding, -minY + padding);
    
    for (const key of hexKeys) {
        const hex = hexes[key];
        const pos = hexPositions[key];
        const isLand = hex.type !== 'ocean';
        
        drawHex(ctx, pos.x, pos.y, hexRadius - 2, getHexColor(hex.type), hex.number, isLand);
    }
    
    // Draw vertices on top
    const vertices = boardData.vertices || {};
    const vertexPositions = {};
    for (const key in vertices) {
        const coords = parseKey(key);
        const pos = cubeToPixel(coords.x, coords.y, coords.z, hexRadius);
        vertexPositions[key] = pos;
        drawVertex(ctx, pos.x, pos.y);
    }
    
    // Draw edges on top
    const edges = boardData.edges || {};
    for (const key in edges) {
        const edge = edges[key];
        const vertexKeys = edge.neighbors.vertices || [];
        if (vertexKeys.length >= 2) {
            const pos1 = vertexPositions[vertexKeys[0]];
            const pos2 = vertexPositions[vertexKeys[1]];
            if (pos1 && pos2) {
                drawEdge(ctx, pos1.x, pos1.y, pos2.x, pos2.y);
            }
        }
    }
    
    return { canvas, hexPositions, vertexPositions };
    return { canvas, hexPositions };
}

function setupBoardRenderer() {
    return {
        render: renderBoard
    };
}

window.BoardRenderer = {
    render: renderBoard
};
