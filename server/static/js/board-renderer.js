/**
 * Catan Board Renderer
 * Renders the Catan board using HTML5 Canvas
 */

// Configuration for the board rendering
const BOARD_CONFIG = {
    hexRadius: 35,       // Size of hexes in pixels
    edgeRadius: 3,       // Not used currently, kept for reference
    clickRadius: 15,     // Pixels to detect clicks on vertices/edges
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
        numberText: '#2c3e50',
        vertexDefault: 'red',
        edgeDefault: 'red'
    }
};

// Global storage for click detection
let boardPositions = {
    hexPositions: {},
    vertexPositions: {},
    edgePositions: {}
};

/**
 * Convert cube coordinates to pixel coordinates for rendering.
 * Uses the formula from hex.md:
 *   px = S * √3 * (x / 3 + z / 6)
 *   py = S * 3/2 * (z / 3)
 * 
 * @param {number} x - Cube x coordinate
 * @param {number} y - Cube y coordinate  
 * @param {number} z - Cube z coordinate
 * @param {number} radius - Hex radius for scaling
 * @returns {object} - {x, y} pixel coordinates
 */
function cubeToPixel(x, y, z, radius) {
    const px = radius * Math.sqrt(3) * (x / 3 + z / 6);
    const py = radius * 3/2 * (z / 3);
    return { x: px, y: py };
}

/**
 * Parse a coordinate key string into (x, y, z) tuple.
 * Key format: "x,y,z" e.g., "3,-3,0"
 * 
 * @param {string} key - Coordinate key string
 * @returns {object} - {x, y, z} coordinates
 */
function parseKey(key) {
    const parts = key.split(',').map(Number);
    return { x: parts[0], y: parts[1], z: parts[2] };
}

/**
 * Draw a single hex on the canvas.
 * 
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} centerX - Center x position
 * @param {number} centerY - Center y position
 * @param {number} radius - Hex radius
 * @param {string} color - Fill color
 * @param {number|null} number - Number token (2-12) or null
 * @param {boolean} isLand - Whether this is a land hex (not ocean)
 */
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

/**
 * Draw a number token circle in the center of a hex.
 * 
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} centerX - Center x position
 * @param {number} centerY - Center y position
 * @param {number} number - The dice number (2-12)
 */
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

/**
 * Get the color for a hex type.
 * 
 * @param {string} hexType - Type of hex (ore, wheat, sheep, brick, wood, desert, ocean)
 * @returns {string} - Hex color code
 */
function getHexColor(hexType) {
    return BOARD_CONFIG.colors[hexType] || BOARD_CONFIG.colors.ocean;
}

/**
 * Draw a vertex (test rendering - red dot).
 * 
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} x - X position
 * @param {number} y - Y position
 */
function drawVertex(ctx, x, y) {
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = BOARD_CONFIG.colors.vertexDefault;
    ctx.fill();
}

/**
 * Draw an edge (test rendering - red line).
 * 
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} x1 - Start x
 * @param {number} y1 - Start y
 * @param {number} x2 - End x
 * @param {number} y2 - End y
 */
function drawEdge(ctx, x1, y1, x2, y2) {
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = BOARD_CONFIG.colors.edgeDefault;
    ctx.lineWidth = 3;
    ctx.stroke();
}

/**
 * Draw a settlement at a vertex position.
 * Settlement appears as a colored square with player color.
 * 
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} x - X position
 * @param {number} y - Y position
 * @param {string} playerColor - Color of the player who owns this settlement
 */
function drawSettlement(ctx, x, y, playerColor) {
    const size = 10;
    ctx.fillStyle = playerColor || '#888888';
    ctx.fillRect(x - size/2, y - size/2, size, size);
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1;
    ctx.strokeRect(x - size/2, y - size/2, size, size);
}

/**
 * Draw a city at a vertex position.
 * City appears as a larger colored shape (double-sized square).
 * 
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} x - X position
 * @param {number} y - Y position
 * @param {string} playerColor - Color of the player who owns this city
 */
function drawCity(ctx, x, y, playerColor) {
    const size = 16;
    ctx.fillStyle = playerColor || '#888888';
    ctx.fillRect(x - size/2, y - size/2, size, size);
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 2;
    ctx.strokeRect(x - size/2, y - size/2, size, size);
}

/**
 * Draw a road on an edge.
 * Road appears as a thick colored line.
 * 
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} x1 - Start x
 * @param {number} y1 - Start y
 * @param {number} x2 - End x
 * @param {number} y2 - End y
 * @param {string} playerColor - Color of the player who owns this road
 */
function drawRoad(ctx, x1, y1, x2, y2, playerColor) {
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = playerColor || '#888888';
    ctx.lineWidth = 6;
    ctx.stroke();
}

/**
 * Main render function - draws the entire board.
 * 
 * @param {object} boardData - Board data from server containing hexes, vertices, edges, players
 * @param {string} canvasId - ID of the canvas element
 * @returns {object} - Object with canvas and position data for click detection
 */
function renderBoard(boardData, canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error('Canvas not found:', canvasId);
        return;
    }
    
    const ctx = canvas.getContext('2d');
    const hexes = boardData.hexes || {};
    const vertices = boardData.vertices || {};
    const edges = boardData.edges || {};
    const players = boardData.players || [];
    
    const hexRadius = BOARD_CONFIG.hexRadius;
    
    // Build player color lookup from players array
    const playerColors = {};
    for (const player of players) {
        if (player.name && player.color) {
            playerColors[player.name] = player.color;
        }
    }
    
    // Calculate canvas size by finding bounding box of all hexes
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
    
    // Store offset for click detection conversion
    const offsetX = -minX + padding;
    const offsetY = -minY + padding;
    
    ctx.translate(offsetX, offsetY);
    
    // Draw all hexes
    for (const key of hexKeys) {
        const hex = hexes[key];
        const pos = hexPositions[key];
        const isLand = hex.type !== 'ocean';
        
        drawHex(ctx, pos.x, pos.y, hexRadius - 2, getHexColor(hex.type), hex.number, isLand);
    }
    
    // Calculate and store vertex positions
    const vertexPositions = {};
    for (const key in vertices) {
        const coords = parseKey(key);
        const pos = cubeToPixel(coords.x, coords.y, coords.z, hexRadius);
        vertexPositions[key] = pos;
        
        // Check if there's a building at this vertex
        const vertex = vertices[key];
        if (vertex.building) {
            const playerColor = playerColors[vertex.building.player] || null;
            if (vertex.building.type === 'settlement') {
                drawSettlement(ctx, pos.x, pos.y, playerColor);
            } else if (vertex.building.type === 'city') {
                drawCity(ctx, pos.x, pos.y, playerColor);
            }
        } else {
            // Draw test vertex dot
            drawVertex(ctx, pos.x, pos.y);
        }
    }
    
    // Calculate and store edge positions
    const edgePositions = {};
    for (const key in edges) {
        const edge = edges[key];
        const vertexKeys = edge.neighbors.vertices || [];
        
        if (vertexKeys.length >= 2) {
            const pos1 = vertexPositions[vertexKeys[0]];
            const pos2 = vertexPositions[vertexKeys[1]];
            
            if (pos1 && pos2) {
                // Store edge position as midpoint for click detection
                edgePositions[key] = {
                    x1: pos1.x, y1: pos1.y,
                    x2: pos2.x, y2: pos2.y,
                    centerX: (pos1.x + pos2.x) / 2,
                    centerY: (pos1.y + pos2.y) / 2
                };
                
                // Check if there's a road at this edge
                if (edge.road) {
                    const playerColor = playerColors[edge.road.player] || null;
                    drawRoad(ctx, pos1.x, pos1.y, pos2.x, pos2.y, playerColor);
                } else {
                    // Draw test edge line
                    drawEdge(ctx, pos1.x, pos1.y, pos2.x, pos2.y);
                }
            }
        }
    }
    
    // Store positions globally for click detection
    boardPositions = {
        hexPositions,
        vertexPositions,
        edgePositions,
        offsetX,
        offsetY
    };
    
    return { canvas, hexPositions, vertexPositions };
}

/**
 * Calculate distance from a point to a line segment.
 * Used for edge click detection.
 * 
 * @param {number} px - Point x
 * @param {number} py - Point y
 * @param {number} x1 - Line start x
 * @param {number} y1 - Line start y
 * @param {number} x2 - Line end x
 * @param {number} y2 - Line end y
 * @returns {number} - Distance from point to line segment
 */
function pointToLineDistance(px, py, x1, y1, x2, y2) {
    const A = px - x1;
    const B = py - y1;
    const C = x2 - x1;
    const D = y2 - y1;
    
    const dot = A * C + B * D;
    const lenSq = C * C + D * D;
    
    let param = -1;
    if (lenSq !== 0) {
        param = dot / lenSq;
    }
    
    let xx, yy;
    
    if (param < 0) {
        xx = x1;
        yy = y1;
    } else if (param > 1) {
        xx = x2;
        yy = y2;
    } else {
        xx = x1 + param * C;
        yy = y1 + param * D;
    }
    
    const dx = px - xx;
    const dy = py - yy;
    
    return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Find the nearest vertex to a click position.
 * 
 * @param {number} clickX - Click x position (relative to canvas origin)
 * @param {number} clickY - Click y position
 * @returns {string|null} - Vertex key if found, null otherwise
 */
function findNearestVertex(clickX, clickY) {
    const { vertexPositions, offsetX, offsetY } = boardPositions;
    const radius = BOARD_CONFIG.clickRadius;
    
    let nearestKey = null;
    let nearestDist = Infinity;
    
    for (const key in vertexPositions) {
        const pos = vertexPositions[key];
        // Adjust for canvas offset
        const adjX = pos.x + offsetX;
        const adjY = pos.y + offsetY;
        
        const dist = Math.sqrt(Math.pow(clickX - adjX, 2) + Math.pow(clickY - adjY, 2));
        
        if (dist < radius && dist < nearestDist) {
            nearestDist = dist;
            nearestKey = key;
        }
    }
    
    return nearestKey;
}

/**
 * Find the nearest edge to a click position.
 * 
 * @param {number} clickX - Click x position (relative to canvas origin)
 * @param {number} clickY - Click y position
 * @returns {string|null} - Edge key if found, null otherwise
 */
function findNearestEdge(clickX, clickY) {
    const { edgePositions, offsetX, offsetY } = boardPositions;
    const radius = BOARD_CONFIG.clickRadius;
    
    let nearestKey = null;
    let nearestDist = Infinity;
    
    for (const key in edgePositions) {
        const edge = edgePositions[key];
        
        // Calculate distance from click to edge line
        const clickAdjX = clickX - offsetX;
        const clickAdjY = clickY - offsetY;
        
        const dist = pointToLineDistance(
            clickAdjX, clickAdjY,
            edge.x1, edge.y1,
            edge.x2, edge.y2
        );
        
        if (dist < radius && dist < nearestDist) {
            nearestDist = dist;
            nearestKey = key;
        }
    }
    
    return nearestKey;
}

/**
 * Main entry point for rendering.
 */
function setupBoardRenderer() {
    return {
        render: renderBoard,
        findNearestVertex,
        findNearestEdge
    };
}

// Export for use in client.js
window.BoardRenderer = {
    render: renderBoard,
    findNearestVertex: findNearestVertex,
    findNearestEdge: findNearestEdge
};
