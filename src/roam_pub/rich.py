"""Rich terminal-rendering utilities for Roam node trees.

Public symbols:

- :data:`DEFAULT_PANEL_PROPS` — the property names rendered in a panel body by default.
- :func:`make_panel` — render a :class:`~roam_pub.roam_node.RoamNode` as a Rich
  :class:`~rich.panel.Panel`.
- :func:`build_rich_tree` — build a list of Rich :class:`~rich.tree.Tree` instances
  from a :data:`~roam_pub.roam_node.NodeNetwork`, one per root node.
"""

from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree as RichTree

from roam_pub.roam_node import NodeNetwork, RoamNode, is_root
from roam_pub.roam_types import Id

DEFAULT_PANEL_PROPS: list[str] = ["heading", "order", "children", "parents", "page"]
"""Property names rendered in the panel body by :func:`make_panel` when no explicit list is given.

``string``/``title`` and ``id`` are always shown in the panel title and are not
included here.  All other :class:`~roam_pub.roam_node.RoamNode` field names are
valid entries.
"""


def _format_node_prop(node: RoamNode, prop: str) -> str:
    """Return a ``name=value`` string for *prop* on *node*, for use in a panel body.

    Args:
        node: The node whose property is to be formatted.
        prop: A :class:`~roam_pub.roam_node.RoamNode` field name.

    Returns:
        A ``"name=value"`` string.  Unknown *prop* names produce ``"name=?"``.
    """
    match prop:
        case "order":
            return f"order={node.order}"
        case "children":
            val = f"[{', '.join(str(c.id) for c in node.children)}]" if node.children else "None"
            return f"children={val}"
        case "parents":
            val = f"[{', '.join(str(p.id) for p in node.parents)}]" if node.parents else "None"
            return f"parents={val}"
        case "page":
            val = str(node.page.id) if node.page is not None else "None"
            return f"page={val}"
        case "time":
            return f"time={node.time}"
        case "user":
            return f"user={node.user.id}"
        case "refs":
            val = f"[{', '.join(str(r.id) for r in node.refs)}]" if node.refs else "None"
            return f"refs={val}"
        case "open":
            return f"open={node.open}"
        case "sidebar":
            return f"sidebar={node.sidebar}"
        case "heading":
            return f"heading={node.heading}"
        case "attrs":
            return f"attrs={node.attrs}"
        case "lookup":
            val = f"[{', '.join(str(lk.id) for lk in node.lookup)}]" if node.lookup else "None"
            return f"lookup={val}"
        case "seen_by":
            val = f"[{', '.join(str(s.id) for s in node.seen_by)}]" if node.seen_by else "None"
            return f"seen_by={val}"
        case "uid":
            return f"uid={node.uid}"
        case "id":
            return f"id={node.id}"
        case _:
            return f"{prop}=?"


def make_panel(node: RoamNode, props: list[str] = DEFAULT_PANEL_PROPS) -> Panel:
    """Render *node* as a Rich Panel for display in a terminal tree.

    The panel title always shows the block string or page title with the node
    ``id`` in parentheses.  An ``H{n}:`` prefix is prepended only when
    ``"heading"`` is included in *props* and the node has a heading level set.
    The panel body shows the remaining properties named in *props* as a single
    formatted line of ``name=value`` pairs; ``heading`` is excluded from the body
    because it is represented by the title prefix.

    Args:
        node: The node to render.
        props: Ordered list of :class:`~roam_pub.roam_node.RoamNode` field names
            to include.  Controls both the ``H{n}:`` title prefix (shown only when
            ``"heading"`` is present) and the body pairs (``heading`` itself is
            never written to the body).  Defaults to :data:`DEFAULT_PANEL_PROPS`.

    Returns:
        A :class:`~rich.panel.Panel` with a labelled title and metadata body.
    """
    text: str = node.string or node.title or f"(uid={node.uid})"
    if node.heading is not None and "heading" in props:
        text = f"H{node.heading}: {text}"
    title: str = f"{text} ({node.id})"
    content: str = "  ".join(_format_node_prop(node, p) for p in props if p != "heading")
    return Panel(Text(content), title=title, expand=False)


def _populate_subtree(node: RoamNode, rich_parent: RichTree, id_map: dict[Id, RoamNode], props: list[str]) -> None:
    """Recursively attach *node*'s children to *rich_parent*.

    Children are resolved via *id_map*, sorted by
    :attr:`~roam_pub.roam_node.RoamNode.order`, and each rendered with
    :func:`make_panel` before being added to the tree.  Children whose ``id``
    is absent from *id_map* are silently skipped.

    Args:
        node: The node whose children are to be rendered.
        rich_parent: The Rich tree node to attach children to.
        id_map: Mapping from Datomic entity id to
            :class:`~roam_pub.roam_node.RoamNode`, used to resolve child stubs.
        props: Property names forwarded to :func:`make_panel` for each child.
    """
    if node.children:
        child_nodes: list[RoamNode] = sorted(
            [id_map[c.id] for c in node.children if c.id in id_map],
            key=lambda n: n.order if n.order is not None else 0,
        )
        for child in child_nodes:
            _populate_subtree(child, rich_parent.add(make_panel(child, props)), id_map, props)


def build_rich_tree(network: NodeNetwork, props: list[str] = DEFAULT_PANEL_PROPS) -> list[RichTree]:
    """Build one Rich tree per root node in *network*.

    Root nodes are determined by :func:`~roam_pub.roam_node.is_root` and sorted
    by :attr:`~roam_pub.roam_node.RoamNode.order`.  Each root becomes the label
    of a top-level :class:`~rich.tree.Tree`; its descendants are populated
    recursively via :func:`make_panel`.

    Args:
        network: The collection of nodes to render.
        props: Ordered list of :class:`~roam_pub.roam_node.RoamNode` field names
            to include in each panel body.  Defaults to :data:`DEFAULT_PANEL_PROPS`.

    Returns:
        One :class:`~rich.tree.Tree` per root node, in order.
    """
    id_map: dict[Id, RoamNode] = {n.id: n for n in network}
    roots: list[RoamNode] = sorted(
        [n for n in network if is_root(n, network)],
        key=lambda n: n.order if n.order is not None else 0,
    )
    trees: list[RichTree] = []
    for root in roots:
        rich_tree: RichTree = RichTree(make_panel(root, props))
        _populate_subtree(root, rich_tree, id_map, props)
        trees.append(rich_tree)
    return trees
