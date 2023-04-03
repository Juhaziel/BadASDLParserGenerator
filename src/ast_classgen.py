# This module implements a parser for a variation of ASDL as an exercise
import re
from dataclasses import dataclass

# Default types: ident, int (or char), string (or str), boolean (or bool), float
#
# Module = 'module' name '{' TypeDef* '}'
# TypeDef = (type_name '=' Type)*
# Type = ProductType | SumType
# ProductType = fields
# SumType = Constructor ('|' Constructor)* ('attributes' fields)?
# Constructor = ctor_name fields?
# fields = '(' field (',' field)* ')'
# field = type_name ('?'|'*'|'+')? field_name

_default_types = {"ident": str, "int": int, "char": int, "string": str, "str": str, "boolean": bool, "bool": bool, "float": float}

def ParseAsdl(asdl_string: str) -> 'Module':
    regex_flag = re.DOTALL | re.MULTILINE
    
    # Extract module name and inside
    asdl_string = re.sub(r"\-\-(.*)$", "", asdl_string, flags=re.MULTILINE)
    m = re.match(r"^\s*module\s+(\w+)\s*\{\s*(.*)\s*\}\s*(attributes\s*)?$", asdl_string, regex_flag)
    if m == None: raise Exception("missing module statement")
    
    mod_name, mod_raw, has_attribs = m.group(1, 2, 3)
    
    def getField() -> 'Field':
        nonlocal mod_raw
        if (m := re.match(r"^\s*(\w+)([\?\*\+])?\s+(\w+)\s*", mod_raw, regex_flag)) == None:
            raise Exception("expected field")
        mod_raw = mod_raw[m.end():]
        type_name, symbol, field_name = m.group(1, 2, 3)
        can_none, can_many = False, False
        if symbol and symbol in "?*": can_none = True
        if symbol and symbol in "*+": can_many = True
        return Field(type_name, field_name, can_none, can_many)
    
    def getFields() -> list['Field']:
        nonlocal mod_raw
        fields = []
        if (m := re.match(r"^\s*\(\s*", mod_raw, regex_flag)) == None:
            raise Exception("expected left parenthesis to begin field list.")
        mod_raw = mod_raw[m.end():]
        while True:
            fields.append(getField())
            if (m := re.match(r"^\s*,\s*", mod_raw, regex_flag)) == None: break
            mod_raw = mod_raw[m.end():]
        if (m := re.match(r"^\s*\)\s*", mod_raw, regex_flag)) == None:
            raise Exception("expected right parenthesis to close field list.")
        mod_raw = mod_raw[m.end():]
        return fields
    
    def getConstructor() -> 'Constructor':
        nonlocal mod_raw
        if (m := re.match(r"^\s*(\w+)\s*", mod_raw, regex_flag)) == None:
            raise Exception("expected name in constructor")
        mod_raw = mod_raw[m.end():]
        ctor_name = m.group(1)
        if not ctor_name[0].isupper():
            raise Exception("constructor name must start with an uppercase later")
        if (m := re.match(r"^\s*\(\s*", mod_raw, regex_flag)) == None:
            return Constructor(ctor_name, [])
        try:
            return Constructor(ctor_name, getFields())
        except Exception as e:
            raise Exception(f"in ctor of '{ctor_name}'") from e
    
    def getSumType() -> 'ProductType':
        nonlocal mod_raw
        ctors = []
        while True:
            ctors.append(getConstructor())
            if (m := re.match(r"^\s*\|\s*", mod_raw, regex_flag)) == None: break
            mod_raw = mod_raw[m.end():]
        attribs = []
        if (m := re.match(r"^\s*attributes\s*", mod_raw, regex_flag)) != None:
            mod_raw = mod_raw[m.end():]
            attribs = getFields()
        return SumType(ctors, attribs)
    
    mod_body: list['TypeDef'] = []
    
    defined = set()
    
    while mod_raw.strip() != "":
        if (m := re.match(r"^\s*(\w+)\s*=\s*", mod_raw, regex_flag)) == None:
            raise Exception("expected type definition")
        mod_raw = mod_raw[m.end():]
        type_name = m.group(1)
        if type_name in defined:
            raise Exception(f"cannot define type '{type_name}' twice.")
        defined.add(type_name)
        try:
            if type_name == "AST" or type_name in _default_types:
                raise Exception(f"cannot redefine basic type.")
            
            if (m := re.match(r"^\s*\(", mod_raw, regex_flag)) == None:
                type = getSumType()
            else:
                type = ProductType(getFields())
            mod_body.append(TypeDef(type_name, type))
        except Exception as e:
            raise Exception(f"in typedef of '{type_name}'") from e
    
    return Module(mod_name, mod_body)

@dataclass
class Module:
    """
    Contains a list of type definitions
    """
    mod_name: str
    typedefs: list['TypeDef']

@dataclass
class TypeDef:
    """
    Contains a type name and its definition
    """
    type_name: str
    type_def: 'AbstractType'

class AbstractType:
    """
    Parent class of type definitions.
    """
    pass

@dataclass
class ProductType(AbstractType):
    """
    Represents a record type which is an aggregate of data.
    """
    fields: list['Field']

@dataclass
class SumType(AbstractType):
    """
    Represents a set of subclasses that are all of the same type, plus attributes shared between all of them.
    """
    ctors: list['Constructor']
    attribs: list['Field']

@dataclass
class Constructor:
    """
    Represents the declaration of a subclass of a SumType
    """
    ctor_name: str
    fields: list['Field']

@dataclass
class Field:
    """
    Represents an actual field of data
    """
    type_name: str
    field_name: str
    can_none: bool = False
    can_many: bool = False

def AsdlToPy(asdl_string: str) -> str:
    import os
    with open(f"{os.path.dirname(__file__)}/ast_basis.py", "r") as f:
        f.readline()
        ast = f.read()
    asdl = ParseAsdl(asdl_string)
    
    def GetTypeName(name: str) -> str:
        if name in _default_types:
            return _default_types[name].__name__
        return f"'{name}'"
    
    def ToParam(field: 'Field') -> str:
        type = GetTypeName(field.type_name)
        if field.can_many:
            type = f"list[{type}]"
        elif field.can_none:
            type = f"{type} | None"
        return f"{field.field_name}: {type}"
    
    def ToAssign(field: 'Field') -> str:
        type = GetTypeName(field.type_name)
        if field.can_many:
            type = f"list[{type}]"
        elif field.can_none:
            type = f"{type} | None"
        return f"self.{field.field_name}: {type} = {field.field_name}"
    
    def GenAbstractClass(name: str, attribs: list['Field']) -> str:
        if len(attribs) == 0:
            return f"class {name}(AST): pass"
        
        names = ", ".join(map(lambda x: f'"{x.field_name}"', attribs))
        params = ", ".join(map(ToParam, attribs))
        assignments = "\n\t\t".join(map(ToAssign, attribs))
        
        return f"class {name}(AST):\n\tdef __init__(self, {params}):\n\t\tself._attribs = ({names},)\n\t\t{assignments}"
    
    def GenDataClass(name: str, fields: list['Field'], parent: str = "AST", parent_attribs: list['Field'] = []) -> str:
        if len(fields) == 0:
            return f"class {name}({parent}): pass"
        
        superctor = ""
        if len(fields) > 0:
            fields_list = "self._fields = (" + ", ".join(map(lambda x: f'"{x.field_name}"', fields)) + ",)"
        else:
            fields_list = ""
        attrib_args = ", ".join(map(lambda x: f"{x.field_name}", parent_attribs))
        attrib_params = ", ".join(map(ToParam, parent_attribs))
        params = ", ".join(map(ToParam, fields))
        if len(parent_attribs) > 0:
            if params.strip() == "":
                params = attrib_args
            else:
                params = ", ".join([attrib_params, params])
            superctor = f"super().__init__({attrib_args})\n\t\t"
        assignments = "".join("\n\t\t" + x for x in map(ToAssign, fields))
        
        return f"class {name}({parent}):\n\tdef __init__(self, {params}):\n\t\t{superctor}{fields_list}{assignments}"
    
    ast += f"\n\n### GENERATED CLASSES FOR {asdl.mod_name} ###"
    
    unique_types = set()
    
    for typedef in asdl.typedefs:
        if isinstance(typedef.type_def, ProductType):
            ast += f"\n\n## TYPE '{typedef.type_name}'\n"
            ast += GenDataClass(typedef.type_name, typedef.type_def.fields)
        elif isinstance(typedef.type_def, SumType):
            ast += f"\n\n## TYPE '{typedef.type_name}'\n"
            ast += GenAbstractClass(typedef.type_name, typedef.type_def.attribs)
            for ctor in typedef.type_def.ctors:
                ast += "\n\n"
                ast += GenDataClass(ctor.ctor_name, ctor.fields, typedef.type_name, typedef.type_def.attribs)
    
    return ast