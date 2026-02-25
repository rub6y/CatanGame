This is a scaled cube–lattice coordinate system that gives unique, integer, global IDs for hexes, edges, and vertices, with clean neighbor logic and no floating-point ambiguity.

1. Base Space: Cube Coordinates

We work in 3D integer space with coordinates:

(x, y, z) ∈ ℤ³

with the invariant:

x + y + z = 0

This defines a 2D hexagonal lattice embedded in 3D.

All objects (hexes, edges, vertices) live in this same space.

2. Scaling the Space

To represent multiple topological elements (cell centers, edges, vertices) without collisions, we scale the lattice by a factor of 3.

This allows:

Integer coordinates only

Clear classification by divisibility

No floating-point rounding

3. Object Classification Rules

Let (x, y, z) satisfy x + y + z = 0.

Object Type	Coordinate Rule	Interpretation
Hex (cell center)	x ≡ y ≡ z ≡ 0 (mod 3)	Center of a hex
Edge midpoint	exactly one coord ≡ 0 (mod 3)	Center of a shared edge
Vertex (corner)	no coord ≡ 0 (mod 3)	Intersection of 3 hexes

These rules are invariants of the system.

4. Hex Coordinates

Each hex occupies one scaled cube coordinate:

H = (3a, 3b, 3c) where a + b + c = 0

These are the canonical hex IDs.

Neighbor Hexes

Neighboring hexes differ by:

±(3, -3, 0)
±(3, 0, -3)
±(0, 3, -3)
5. Edge Coordinates

Edges lie between two neighboring hexes.

From a hex center (x, y, z), its 6 edges are at:

(x, y, z) + d_edge

where:

d_edge ∈ {
 ( 1,-1, 0),
 ( 1, 0,-1),
 ( 0, 1,-1),
 (-1, 1, 0),
 (-1, 0, 1),
 ( 0,-1, 1)
}
Properties

Each edge coordinate is shared by exactly 2 hexes

Edge IDs are globally unique

No duplicate storage needed

6. Vertex Coordinates

Vertices lie where three hexes meet.

From a hex center (x, y, z), its 6 vertices are at:

(x, y, z) + d_vertex

where:

d_vertex ∈ {
 ( 1,-2, 1),
 ( 2,-1,-1),
 ( 1, 1,-2),
 (-1, 2,-1),
 (-2, 1, 1),
 (-1,-1, 2)
}
Properties

Each vertex belongs to exactly 3 hexes

Vertex IDs are globally unique

Perfect for graph nodes

7. Neighborhood Relationships

All adjacency is derived algebraically.

Hex → Hex

Add one of the 6 hex direction vectors.

Hex → Edges

Add the 6 edge direction vectors.

Hex → Vertices

Add the 6 vertex direction vectors.

Edge → Vertices

Each edge touches 2 vertices, found by adding/subtracting one vertex offset.

Vertex → Hexes

Each vertex has 3 neighboring hexes located at offsets divisible by 3.

No lookup tables are required — only integer math.

8. Rendering Coordinates

To render in 2D, convert cube coordinates → pixel space.

For hex centers:

px = S * √3 * (x / 3 + z / 6)
py = S * 3/2 * (z / 3)

Where S is hex radius.

Edges and vertices project naturally using the same formula.

9. Key System

Coordinates are serialized as strings:

"x,y,z"

Example:

"4,-5,1"   // vertex
"3,-3,0"   // hex
"1,-1,0"   // edge

These keys are stable across:

Saves

Network sync

Replays

Diffing

10. Why This System Works

This system guarantees:

✔ Unique identity for every geometric feature
✔ Integer-only math
✔ Deterministic neighbors
✔ Clean graph representation
✔ Easy serialization

It is effectively a topological index space, not just a coordinate system.

11. Mental Model (Very Important)

Think of it as:

“A triangular lattice embedded in cube space, where hexes, edges, and vertices occupy different parity classes.”

Once you internalize that, everything becomes mechanical.
