"""Rich terminal-rendering utilities for Roam node trees.

Public symbols:

- :data:`DEFAULT_PANEL_PROPS` — the property names rendered in a panel body by default.
- :func:`make_panel` — render a :class:`~roam_pub.roam_node.RoamNode` as a Rich
  :class:`~rich.panel.Panel`.
- :func:`build_rich_tree` — build a Rich :class:`~rich.tree.Tree` from a
  :class:`~roam_pub.roam_node.NodeTree` using a depth-first traversal.
"""

import logging

from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree as RichTree

from roam_pub.roam_node import NodeTree, NodeTreeDFSIterator, RoamNode
from roam_pub.roam_primitives import Id, IMAGE_LINK_RE

logger = logging.getLogger(__name__)

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
        case "props":
            return f"props={node.props}"
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
    ``id`` in parentheses.  The title text is determined as follows:

    - If the block string contains a Cloud Firestore image link matching
      :data:`~roam_pub.roam_primitives.IMAGE_LINK_RE`, the title reads
      ``IMAGE [<alt>](FIRESTORE_URL)``.
    - Otherwise, if ``"heading"`` is in *props* and the node has a heading level,
      an ``H{n}:`` prefix is prepended.
    - Otherwise the raw block string or page title is used as-is.

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
    logger.debug("node=%r, props=%r", node, props)
    text: str = node.string or node.title or f"(uid={node.uid})"
    if node.string is not None and (m := IMAGE_LINK_RE.search(node.string)):
        title: str = f"IMAGE [{m.group('alt')}](FIRESTORE_URL) ({node.id})"
    elif node.heading is not None and "heading" in props:
        title = f"H{node.heading}: {text} ({node.id})"
    else:
        title = f"{text} ({node.id})"
    content: str = "  ".join(_format_node_prop(node, p) for p in props if p != "heading")
    return Panel(Text(content), title=title, expand=False)


def build_rich_tree(tree: NodeTree, props: list[str] = DEFAULT_PANEL_PROPS) -> RichTree:
    """Build a Rich tree from *tree* using a depth-first traversal.

    Iterates *tree* in pre-order depth-first order via
    :meth:`~roam_pub.roam_node.NodeTree.dfs`, attaching each node as a Rich
    panel under its parent in the rendered tree.

    Args:
        tree: The :class:`~roam_pub.roam_node.NodeTree` to render.
        props: Ordered list of :class:`~roam_pub.roam_node.RoamNode` field names
            to include in each panel body.  Defaults to :data:`DEFAULT_PANEL_PROPS`.

    Returns:
        A :class:`~rich.tree.Tree` rooted at the single root node of *tree*.
    """
    logger.debug("tree=%r, props=%r", tree, props)
    child_to_parent: dict[Id, Id] = {c.id: n.id for n in tree.network if n.children for c in n.children}
    rich_node_map: dict[Id, RichTree] = {}
    dfs_iter: NodeTreeDFSIterator = tree.dfs()
    root_node: RoamNode = next(dfs_iter)
    root_rich: RichTree = RichTree(make_panel(root_node, props))
    rich_node_map[root_node.id] = root_rich
    for node in dfs_iter:
        parent_rich: RichTree = rich_node_map[child_to_parent[node.id]]
        rich_node_map[node.id] = parent_rich.add(make_panel(node, props))
    return root_rich
