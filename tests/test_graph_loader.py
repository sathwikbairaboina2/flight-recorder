import pytest
from langgraph.graph import StateGraph

from flight_recorder.graph_loader import GraphLoadError, load_builder, topology


def test_loads_compiled_graph():
    assert isinstance(load_builder("flight_recorder.samples:graph"), StateGraph)


def test_loads_uncompiled_builder(tmp_path):
    (tmp_path / "fr_user_graph.py").write_text(
        "from flight_recorder.samples import build\nbuilder = build()\nnot_a_graph = 3\n"
    )
    assert isinstance(load_builder("fr_user_graph:builder", cwd=tmp_path), StateGraph)
    with pytest.raises(GraphLoadError, match="not a StateGraph"):
        load_builder("fr_user_graph:not_a_graph", cwd=tmp_path)


@pytest.mark.parametrize("spec", ["no_colon", "missing_mod_xyz:graph", "flight_recorder.samples:nope"])
def test_bad_specs(spec):
    with pytest.raises(GraphLoadError):
        load_builder(spec)


def test_topology():
    topo = topology(load_builder("flight_recorder.samples:graph"))
    assert topo["nodes"] == ["__start__", "plan", "tools", "answer", "__end__"]
    assert {"source": "plan", "target": "tools", "conditional": False} in topo["edges"]
