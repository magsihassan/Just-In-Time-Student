import time

class CompileError(Exception):
    pass

class LR1Parser:
    def __init__(self, tokens, is_lalr=False):
        self.tokens = tokens
        self.is_lalr = is_lalr
        self.errors = []
        self.Grammar = {
            "S'": [["Program"]],
            "Program": [["StatementList"]],
            "StatementList": [["Statement", "StatementList"], []],
            "Statement": [["VarDecl"], ["FuncDecl"], ["Assignment"], ["IfStmt"], ["WhileStmt"], ["ReturnStmt"], ["PrintStmt"], ["ExprStmt"]],
            "VarDecl": [["Type", "IDENTIFIER", "=", "Expr", ";"], ["Type", "IDENTIFIER", ";"]],
            "Type": [["int"], ["float"], ["string"], ["void"]],
            "FuncDecl": [["Type", "IDENTIFIER", "(", "ParamListOpt", ")", "Block"]],
            "ParamListOpt": [["ParamList"], []],
            "ParamList": [["Type", "IDENTIFIER", ",", "ParamList"], ["Type", "IDENTIFIER"]],
            "Block": [["{", "StatementList", "}"]],
            "Assignment": [["IDENTIFIER", "=", "Expr", ";"]],
            "IfStmt": [["if", "(", "Expr", ")", "Block", "else", "Block"], ["if", "(", "Expr", ")", "Block"]],
            "WhileStmt": [["while", "(", "Expr", ")", "Block"]],
            "ReturnStmt": [["return", "Expr", ";"], ["return", ";"]],
            "PrintStmt": [["print", "(", "Expr", ")", ";"]],
            "ExprStmt": [["Expr", ";"]],
            "Expr": [["Comp"]],
            "Comp": [["Comp", "==", "Add"], ["Comp", "!=", "Add"], ["Comp", "<", "Add"], ["Comp", ">", "Add"], ["Comp", "<=", "Add"], ["Comp", ">=", "Add"], ["Comp", "&&", "Add"], ["Comp", "||", "Add"], ["Add"]],
            "Add": [["Add", "+", "Mul"], ["Add", "-", "Mul"], ["Mul"]],
            "Mul": [["Mul", "*", "Unary"], ["Mul", "/", "Unary"], ["Mul", "%", "Unary"], ["Unary"]],
            "Unary": [["-", "Unary"], ["!", "Unary"], ["Primary"]],
            "Primary": [["NUMBER"], ["FLOAT"], ["STRING"], ["IDENTIFIER"], ["IDENTIFIER", "(", "ArgListOpt", ")"], ["(", "Expr", ")"]],
            "ArgListOpt": [["ArgList"], []],
            "ArgList": [["Expr", ",", "ArgList"], ["Expr"]]
        }
        self.Terminals = {"int", "float", "string", "void", "if", "else", "while", "return", "print", "(", ")", "{", "}", ";", "=", "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=", "&&", "||", ",", "!", "IDENTIFIER", "NUMBER", "FLOAT", "STRING", "EOF"}
        self.NonTerminals = set(self.Grammar.keys())
        
        # Flatten grammar for easy indexing
        self.rules = []
        for nt, rhss in self.Grammar.items():
            for rhs in rhss:
                self.rules.append((nt, rhs))

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

    def first_of_seq(self, seq, first_dict):
        res = set()
        for sym in seq:
            res |= (first_dict[sym] - {""})
            if "" not in first_dict[sym]:
                break
        else:
            res.add("")
        return res

    def generate_tables(self):
        first = self.compute_first()
        
        def closure1(items):
            c = set(items)
            changed = True
            while changed:
                new_items = set()
                for nt, ridx, dot, la in c:
                    rule = self.Grammar[nt][ridx]
                    if dot < len(rule):
                        next_sym = rule[dot]
                        if next_sym in self.NonTerminals:
                            beta_la = rule[dot+1:] + [la]
                            for b_la in self.first_of_seq(beta_la, first):
                                if b_la == "": continue
                                for i in range(len(self.Grammar[next_sym])):
                                    new_items.add((next_sym, i, 0, b_la))
                old_len = len(c)
                c |= new_items
                changed = len(c) > old_len
            return frozenset(c)
            
        def goto1(items, symbol):
            new_items = set()
            for nt, ridx, dot, la in items:
                rule = self.Grammar[nt][ridx]
                if dot < len(rule) and rule[dot] == symbol:
                    new_items.add((nt, ridx, dot+1, la))
            return closure1(new_items)
            
        initial_item = ("S'", 0, 0, "EOF")
        initial_state = closure1({initial_item})
        
        states = [initial_state]
        state_map = {initial_state: 0}
        transitions = {}
        
        q = [0]
        while q:
            curr_idx = q.pop(0)
            curr_state = states[curr_idx]
            symbols = set()
            for nt, ridx, dot, la in curr_state:
                rule = self.Grammar[nt][ridx]
                if dot < len(rule):
                    symbols.add(rule[dot])
            
            for sym in symbols:
                next_state = goto1(curr_state, sym)
                if not next_state: continue
                if next_state not in state_map:
                    state_map[next_state] = len(states)
                    states.append(next_state)
                    q.append(state_map[next_state])
                transitions[(curr_idx, sym)] = state_map[next_state]
                
        # LALR Merging
        if self.is_lalr:
            core_map = {}
            for i, state in enumerate(states):
                core = frozenset((nt, ridx, dot) for nt, ridx, dot, la in state)
                if core not in core_map:
                    core_map[core] = []
                core_map[core].append(i)
                
            merged_states = []
            merged_state_map = {}
            for core, indices in core_map.items():
                new_idx = len(merged_states)
                merged_items = set()
                for idx in indices:
                    merged_items |= states[idx]
                    merged_state_map[idx] = new_idx
                merged_states.append(frozenset(merged_items))
                
            states = merged_states
            
            lalr_transitions = {}
            for (f, sym), t in transitions.items():
                new_f = merged_state_map[f]
                new_t = merged_state_map[t]
                lalr_transitions[(new_f, sym)] = new_t
            transitions = lalr_transitions
                
        # Build ACTION and GOTO tables
        action = [{} for _ in states]
        goto_table = [{} for _ in states]
        
        for state_idx, state in enumerate(states):
            for item in state:
                nt, ridx, dot, la = item
                rule = self.Grammar[nt][ridx]
                if dot < len(rule):
                    sym = rule[dot]
                    if sym in self.Terminals:
                        next_state = transitions.get((state_idx, sym))
                        if next_state is not None:
                            if sym in action[state_idx] and action[state_idx][sym] != ('s', next_state):
                                pass # Shift-Shift conflict (should not happen in valid LR1)
                            action[state_idx][sym] = ('s', next_state)
                    elif sym in self.NonTerminals:
                        next_state = transitions.get((state_idx, sym))
                        if next_state is not None:
                            goto_table[state_idx][sym] = next_state
                else:
                    if nt == "S'":
                        action[state_idx]["EOF"] = ('acc', 0)
                    else:
                        if la in action[state_idx]:
                            exist_act = action[state_idx][la]
                            if exist_act[0] == 's':
                                pass # Shift-Reduce, default to shift
                            elif exist_act[0] == 'r':
                                pass # Reduce-Reduce, favor first rule
                        else:
                            action[state_idx][la] = ('r', nt, ridx, len(rule))
        return action, goto_table

    def parse(self):
        try:
            action, goto_table = self.generate_tables()
        except Exception as e:
            self.errors.append(f"Failed to generate LR(1) tables: {str(e)}")
            return None
            
        stack = [0]
        sym_stack = []
        pos = 0
        
        while True:
            state = stack[-1]
            if pos < len(self.tokens):
                tok = self.tokens[pos]
            else:
                tok = self.tokens[-1] # EOF
                
            sym = self._get_token_sym(tok)
            
            act = action[state].get(sym)
            if not act:
                line = tok['line'] if 'line' in tok else 'unknown'
                self.errors.append(f"Syntax Error: Unexpected token '{sym}' at line {line}")
                return None
                
            if act[0] == 's':
                stack.append(act[1])
                sym_stack.append({'type': 'Terminal', 'name': sym, 'token': tok})
                pos += 1
            elif act[0] == 'r':
                nt, ridx, rule_len = act[1], act[2], act[3]
                children = []
                for _ in range(rule_len):
                    stack.pop()
                    children.append(sym_stack.pop())
                children.reverse()
                
                # Optimize tree: collapse single-child nodes to reduce depth
                if len(children) == 1 and nt not in ("Program", "StatementList", "Block", "Statement"):
                    node = children[0]
                else:
                    node = {'type': 'CSTNode', 'name': nt, 'children': children}
                
                prev_state = stack[-1]
                next_state = goto_table[prev_state].get(nt)
                if next_state is None:
                    self.errors.append(f"Syntax Error: Invalid reduction GOTO at state {prev_state}")
                    return None
                stack.append(next_state)
                sym_stack.append(node)
                
            elif act[0] == 'acc':
                return sym_stack[0]
