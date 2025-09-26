import pytest
from voide.graph import Graph, Node, Edge
from voide.compiler import compile
from voide.errors import CycleError

def test_graph_serialization_roundtrip():
    g = Graph()
    n = Node(id="n1", type_name="A", config={})
    g.add_node(n)
    e = Edge(from_node="n1", from_port="out", to_node="n1", to_port="in")
    g.add_edge(e)
    d = g.to_dict()
    g2 = Graph.from_dict(d)
    assert len(g2.nodes) == 1 and len(g2.edges) == 1

def test_topo_sort_cycle():
    g = Graph()
    g.add_node(Node(id="a", type_name="A", config={}))
    g.add_node(Node(id="b", type_name="B", config={}))
    g.add_edge(Edge("a", "out", "b", "in"))
    g.add_edge(Edge("b", "out", "a", "in"))
    with pytest.raises(CycleError):
        g.topo_sort()

def test_runner_simple_chain():
    def op_a(msg, cfg, c): return {"x": msg.get("x", 0) * 2}
    def op_b(msg, cfg, c): return {"y": msg.get("x", 0) + 3}
    container = {"ops": {"A": op_a, "B": op_b}}
    g = Graph()
    g.add_node(Node(id="n1", type_name="A", config={}))
    g.add_node(Node(id="n2", type_name="B", config={}))
    g.add_edge(Edge("n1", "out", "n2", "in"))
    runner = compile(g, container)
    out = runner.run({"x": 5})
    assert out["n1"]["x"] == 10
    assert out["n2"]["y"] == 13

def test_runner_fan_in_fan_out():
    def op_a(msg, cfg, c): return {"v": cfg.get("add", 1)}
    def op_c(msg, cfg, c): return {"sum": sum(msg.get(k, 0) for k in msg)}
    container = {"ops": {"A": op_a, "C": op_c}}
    g = Graph()
    g.add_node(Node(id="a1", type_name="A", config={"add": 2}))
    g.add_node(Node(id="a2", type_name="A", config={"add": 5}))
    g.add_node(Node(id="c", type_name="C", config={}))
    g.add_edge(Edge("a1", "out", "c", "v1"))
    g.add_edge(Edge("a2", "out", "c", "v2"))
    runner = compile(g, container)
    out = runner.run({})
    assert out["c"]["sum"] == 7

