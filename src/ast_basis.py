# This file is used as a basis for the file generated by ast_classgen.py
from __future__ import annotations
from dataclasses import dataclass

"""
https://docs.python.org/3/library/ast.html
"""

@dataclass  
class AST:
    _fields: tuple[str, ...] = ()
    _attribs: tuple[str, ...] = ()
    symref: any = None # A reference to a symbol in a symbol table
    lineno: int | None = None
    col_offset: int | None = None
    end_lineno: int | None = None
    end_col_offset: int | None = None

def get_source_segment(source: str, node: 'AST', padded: bool = False) -> str | None:
    """
    Get the source segment corresponding to this node.
    
    Returns None if location data is missing.
    
    https://docs.python.org/3/library/ast.html#ast.get_source_segment
    """
    lineno, col_offset, end_lineno, end_col_offset = node.lineno, node.col_offset, node.end_lineno, node.end_col_offset
    
    if None in (lineno, col_offset, end_lineno, end_col_offset): return None
    if padded:
        col_offset = 0
    
    lines = []
    cur_line = ""
    for c in source:
        if len(lines) == end_lineno: break
        if c == "\n":
            lines.append(cur_line)
            cur_line = ""
            continue
        cur_line += c
    if cur_line != "": lines.append(cur_line)
    del c, cur_line
    
    for _ in range(lineno-1): lines.pop(0)
    lines[end_lineno-lineno] = lines[end_lineno-lineno][:end_col_offset+1]
    lines[0] = lines[0][col_offset:]
    return "\n".join(lines)

def copy_location(old_node: 'AST', new_node: 'AST') -> 'AST':
    """
    Copies `old_node`'s location data to `new_node` and returns `new_node`
    """
    new_node.lineno = old_node.lineno
    new_node.col_offset = old_node.col_offset
    new_node.end_lineno = old_node.end_lineno
    new_node.end_col_offset = old_node.end_col_offset
    return new_node
    
def fix_missing_locations(node: 'AST') -> 'AST':
    """
    https://docs.python.org/3/library/ast.html#ast.fix_missing_locations
    """
    def _fix(node: 'AST', lineno, col_offset, end_lineno, end_col_offset):
        if node.lineno == None: node.lineno = lineno
        else: lineno = node.lineno
        
        if node.col_offset == None: node.col_offset = col_offset
        else: col_offset = node.col_offset
        
        if node.end_lineno == None: node.end_lineno = end_lineno
        else: end_lineno = node.end_lineno
        
        if node.end_col_offset == None: node.end_col_offset = end_col_offset
        else: end_col_offset = node.end_col_offset
        
        for child in iter_child_nodes(node):
            _fix(child, lineno, col_offset, end_lineno, end_col_offset)
    _fix(node, 1, 0, 1, 0)
    return node

def increment_lineno(node: 'AST', n=1) -> 'AST':
    """
    Increments the line number of this node and all of its descendants by n
    
    https://docs.python.org/3/library/ast.html#ast.increment_lineno
    """
    for child in walk(node):
        if child.lineno != None: child.lineno += n
        if child.end_lineno != None: child.end_lineno += n
    return node

def iter_fields(node: 'AST') -> tuple[str, any]:
    """
    Yield a tuple `(name, value)` for each field of the specified node.
    
    https://docs.python.org/3/library/ast.html#ast.iter_fields
    """
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass

def iter_attribs(node: 'AST') -> tuple[str, any]:
    """
    Yield a tuple `(name, value)` for each attribute of the specified node.
    """
    for attrib in node._attribs:
        try:
            yield attrib, getattr(node, attrib)
        except AttributeError:
            pass

def iter_child_nodes(node: 'AST') -> 'AST':
    """
    Yield all direct child nodes of node.
    
    https://docs.python.org/3/library/ast.html#ast.iter_child_nodes
    """
    for _, attrib in iter_attribs(node):
        if isinstance(attrib, AST):
            yield attrib
        elif isinstance(attrib, list):
            for item in attrib:
                if isinstance(item, AST):
                    yield item
    for _, field in iter_fields(node):
        if isinstance(field, AST):
            yield field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, AST):
                    yield item

def walk(node) -> 'AST':
    """
    Recursively yield all descendants in BFS. The order of child nodes is unspecified.
    
    https://docs.python.org/3/library/ast.html#ast.walk
    """
    from collections import deque
    todo = deque([node])
    while todo:
        node = todo.popleft()
        todo.extend(iter_child_nodes(node))
        yield node

class NodeVisitor:
    """
    Basically the same as the ast package's NodeVisitor, just worse.
    
    https://docs.python.org/3/library/ast.html#ast.NodeVisitor
    """
    def visit(self, node) -> 'AST':
        """Visit a node"""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)
        
    def generic_visit(self, node) -> 'AST':
        """Called if nothing else matches the specified node."""
        for child in iter_child_nodes(node):
            self.visit(child)
        return node

class NodeTransformer(NodeVisitor):
    """
    A NodeVisitor that walks the tree and replaces nodes with the value returned by their visitor method's return value.
    If the return value is None, the node will be removed.
    
    Child nodes must be transformed or have generic_visit called on them.
    
    https://docs.python.org/3/library/ast.html#ast.NodeTransformer
    """
    def generic_visit(self, node) -> 'AST':
        for attrib, old in iter_attribs(node):
            if isinstance(old, list):
                new = []
                for value in old:
                    if isinstance(value, AST):
                        value = self.visit(old)
                        if value is None:
                            continue
                        elif isinstance(value, list):
                            new.extend(value)
                            continue
                        else:
                            new.append(value)
                            continue
                    new.append(value)
                old[:] = new
            elif isinstance(old, AST):
                new = self.visit(old)
                if new is None:
                    delattr(node, attrib)
                else:
                    setattr(node, attrib, new)
        for field, old in iter_fields(node):
            if isinstance(old, list):
                new = []
                for value in old:
                    if isinstance(value, AST):
                        value = self.visit(old)
                        if value is None:
                            continue
                        elif isinstance(value, list):
                            new.extend(value)
                            continue
                        else:
                            new.append(value)
                            continue
                    new.append(value)
                old[:] = new
            elif isinstance(old, AST):
                new = self.visit(old)
                if new is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new)
        return node