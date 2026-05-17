class LL1Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.errors = []
        self.Grammar = {
            "Program": [["StatementList"]],
            "StatementList": [["Statement", "StatementList"], []],
            "Statement": [["Type", "IDENTIFIER", "StatementTail"], ["if", "(", "Expr", ")", "Block", "IfTail"], ["while", "(", "Expr", ")", "Block"], ["return", "ReturnTail"], ["print", "(", "Expr", ")", ";"], ["Expr", ";"]],
            "StatementTail": [["=", "Expr", ";"], [";"], ["(", "ParamListOpt", ")", "Block"]],
            "IfTail": [["else", "Block"], []],
            "ReturnTail": [["Expr", ";"], [";"]],
            "Type": [["int"], ["float"], ["string"], ["void"]],
            "ParamListOpt": [["ParamList"], []],
            "ParamList": [["Type", "IDENTIFIER", "ParamListTail"]],
            "ParamListTail": [[",", "ParamList"], []],
            "Block": [["{", "StatementList", "}"]],
            "Expr": [["Comp"]],
            "Comp": [["Add", "CompTail"]],
            "CompTail": [["==", "Add", "CompTail"], ["!=", "Add", "CompTail"], ["<", "Add", "CompTail"], [">", "Add", "CompTail"], ["<=", "Add", "CompTail"], [">=", "Add", "CompTail"], ["&&", "Add", "CompTail"], ["||", "Add", "CompTail"], []],
            "Add": [["Mul", "AddTail"]],
            "AddTail": [["+", "Mul", "AddTail"], ["-", "Mul", "AddTail"], []],
            "Mul": [["Unary", "MulTail"]],
            "MulTail": [["*", "Unary", "MulTail"], ["/", "Unary", "MulTail"], ["%", "Unary", "MulTail"], []],
            "Unary": [["-", "Unary"], ["!", "Unary"], ["Primary"]],
            "Primary": [["NUMBER"], ["FLOAT"], ["STRING"], ["IDENTIFIER", "PrimaryTail"], ["(", "Expr", ")"]],
            "PrimaryTail": [["(", "ArgListOpt", ")"], ["=", "Expr"], []],
            "ArgListOpt": [["ArgList"], []],
            "ArgList": [["Expr", "ArgListTail"]],
            "ArgListTail": [[",", "ArgList"], []]
        }
        self.Terminals = {"int", "float", "string", "void", "if", "else", "while", "return", "print", "(", ")", "{", "}", ";", "=", "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=", "&&", "||", ",", "!", "IDENTIFIER", "NUMBER", "FLOAT", "STRING", "EOF"}
        self.NonTerminals = set(self.Grammar.keys())

    def _get_token_sym(self, tok):
        if tok['type'] in ('KEYWORD', 'OPERATOR', 'DELIMITER'):
            return tok['value']
        elif tok['type'] in ('IDENTIFIER', 'NUMBER', 'FLOAT', 'STRING', 'EOF'):
            return tok['type']
        return tok['value']

    def compute_first(self):
        first = {s: set() for s in self.Terminals | self.NonTerminals}
        for t in self.Terminals:
            first[t].add(t)
        first[""] = set([""])
        
        changed = True
        while changed:
            changed = False
            for nt, rhss in self.Grammar.items():
                for rule in rhss:
                    if not rule:
                        if "" not in first[nt]:
                            first[nt].add("")
                            changed = True
                        continue
                    for sym in rule:
                        before_len = len(first[nt])
                        first[nt] |= (first[sym] - {""})
                        if len(first[nt]) > before_len:
                            changed = True
                        if "" not in first[sym]:
                            break
                    else:
                        if "" not in first[nt]:
                            first[nt].add("")
                            changed = True
        return first

    def compute_follow(self, first):
        follow = {nt: set() for nt in self.NonTerminals}
        follow["Program"].add("EOF")
        
        changed = True
        while changed:
            changed = False
            for nt, rhss in self.Grammar.items():
                for rule in rhss:
                    for i, sym in enumerate(rule):
                        if sym in self.NonTerminals:
                            trailer = set()
                            if i + 1 < len(rule):
                                for nxt in rule[i+1:]:
                                    trailer |= (first[nxt] - {""})
                                    if "" not in first[nxt]:
                                        break
                                else:
                                    trailer.add("")
                            else:
                                trailer.add("")
                                
                            before_len = len(follow[sym])
                            follow[sym] |= (trailer - {""})
                            if "" in trailer:
                                follow[sym] |= follow[nt]
                            if len(follow[sym]) > before_len:
                                changed = True
        return follow

    def first_of_seq(self, seq, first_dict):
        if not seq: return {""}
        res = set()
        for sym in seq:
            res |= (first_dict[sym] - {""})
            if "" not in first_dict[sym]:
                break
        else:
            res.add("")
        return res

    def generate_table(self):
        first = self.compute_first()
        follow = self.compute_follow(first)
        
        M = {nt: {} for nt in self.NonTerminals}
        
        for nt, rhss in self.Grammar.items():
            for ridx, rule in enumerate(rhss):
                first_alpha = self.first_of_seq(rule, first)
                for a in first_alpha - {""}:
                    if a not in M[nt]:
                        M[nt][a] = []
                    if ridx not in M[nt][a]:
                        M[nt][a].append(ridx)
                if "" in first_alpha:
                    for b in follow[nt]:
                        if b not in M[nt]:
                            M[nt][b] = []
                        if ridx not in M[nt][b]:
                            M[nt][b].append(ridx)
                            
        # Resolve conflicts by taking the first rule to allow parsing
        # (Though a perfect LL1 grammar should have no conflicts)
        for nt in M:
            for t in M[nt]:
                M[nt][t] = M[nt][t][0]
                
        return M

    def flatten_tree(self, node):
        if not node.get('children'):
            return
        
        new_children = []
        for child in node['children']:
            self.flatten_tree(child)
            if child.get('type') == 'CSTNode' and child['name'].endswith('Tail'):
                new_children.extend(child.get('children', []))
            elif child.get('type') == 'CSTNode' and child['name'] == 'StatementList':
                new_children.extend(child.get('children', []))
            elif child.get('type') == 'CSTNode' and child['name'] in ('ParamListOpt', 'ArgListOpt') and not child.get('children'):
                continue # remove empty opts
            else:
                new_children.append(child)
                
        # Also collapse single-child intermediate nodes for extra minimalism
        if len(new_children) == 1 and node['name'] not in ("Program", "StatementList", "Block", "Statement"):
            node.clear()
            node.update(new_children[0])
            return
            
        node['children'] = new_children

    def parse(self):
        M = self.generate_table()
        
        stack = [("EOF", None), ("Program", None)] # (symbol, parent_node)
        
        root = {'type': 'CSTNode', 'name': 'Program', 'children': []}
        stack[-1] = ("Program", root)
        
        pos = 0
        while len(stack) > 1: # stop when only EOF is left
            sym, node_ref = stack.pop()
            
            if pos < len(self.tokens):
                tok = self.tokens[pos]
            else:
                tok = {'type': 'EOF', 'value': 'EOF'}
                
            la = self._get_token_sym(tok)
            
            if sym in self.Terminals:
                if sym == la:
                    node_ref.update({'type': 'Terminal', 'name': sym, 'token': tok})
                    pos += 1
                else:
                    line = tok.get('line', 'unknown')
                    self.errors.append(f"Syntax Error: Expected '{sym}', got '{la}' at line {line}")
                    return None
            elif sym in self.NonTerminals:
                if la in M[sym]:
                    ridx = M[sym][la]
                    rule = self.Grammar[sym][ridx]
                    
                    if not rule:
                        node_ref['children'] = []
                    else:
                        node_ref['children'] = [{'type': 'CSTNode', 'name': s} if s in self.NonTerminals else {} for s in rule]
                        
                        # Push in reverse order
                        for i in range(len(rule) - 1, -1, -1):
                            stack.append((rule[i], node_ref['children'][i]))
                else:
                    line = tok.get('line', 'unknown')
                    self.errors.append(f"Syntax Error: Unexpected token '{la}' when parsing {sym} at line {line}")
                    return None
            else:
                self.errors.append(f"Unknown symbol on stack: {sym}")
                return None
                
        if self.errors:
            return None
            
        self.flatten_tree(root)
        return root
