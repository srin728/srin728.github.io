テスト用の文章です

## LP Formulation of Minimum Vertex Cover

Let $G = (V, E)$ be an undirected graph.

We define a variable $x_v \in [0, 1]$ for each $v \in V$.

**Linear Program:**

Minimize:
$$
\sum_{v \in V} x_v
$$

Subject to:
$$
x_u + x_v \geq 1 \quad \text{for all } \{u, v\} \in E
$$

$$
0 \leq x_v \leq 1 \quad \text{for all } v \in V
$$