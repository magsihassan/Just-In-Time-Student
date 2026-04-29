import re
import json

class CompileError(Exception):
    pass

# --- Phase 1: Lexical Analysis ---
class Lexer:
    def __init__(self, source_code):
        self.source = source_code
        self.tokens = []
        self.pos = 0
        self.line = 1
        self.col = 1

        self.keywords = {'int', 'float', 'string', 'void', 'if', 'else', 'while', 'return'}
        
        # Regex patterns
        self.rules = [
            ('WHITESPACE', r'\s+'),
            ('FLOAT', r'\d+\.\d+'),
            ('NUMBER', r'\d+'),
            ('STRING', r'"[^"]*"'),
            ('IDENTIFIER', r'[a-zA-Z_]\w*'),
            ('OPERATOR', r'==|!=|<=|>=|&&|\|\||[+\-*/%<>=!]'),
            ('DELIMITER', r'[(){}[\];,]')
        ]
        
    def tokenize(self):
        while self.pos < len(self.source):
            match = None
            for kind, pattern in self.rules:
                regex = re.compile(pattern)
                match = regex.match(self.source, self.pos)
                if match:
                    value = match.group(0)
                    if kind != 'WHITESPACE':
                        if kind == 'IDENTIFIER' and value in self.keywords:
                            kind = 'KEYWORD'
                        self.tokens.append({
                            'type': kind,
                            'value': value,
                            'line': self.line,
                            'col': self.col
                        })
                    
                    # Update line and col
                    newlines = value.count('\n')
                    if newlines > 0:
                        self.line += newlines
                        self.col = len(value) - value.rfind('\n')
                    else:
                        self.col += len(value)
                    
                    self.pos = match.end()
                    break
            
            if not match:
                raise CompileError(f"Lexical Error at line {self.line}, col {self.col}: Unexpected character '{self.source[self.pos]}'")
        
        self.tokens.append({'type': 'EOF', 'value': '', 'line': self.line, 'col': self.col})
        return self.tokens

# --- Phase 2: Syntax Analysis ---
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def consume(self, expected_type=None, expected_value=None):
        tok = self.current()
        if expected_type and tok['type'] != expected_type:
            raise CompileError(f"Syntax Error: Expected type {expected_type}, got {tok['type']} at line {tok['line']}")
        if expected_value and tok['value'] != expected_value:
            raise CompileError(f"Syntax Error: Expected '{expected_value}', got '{tok['value']}' at line {tok['line']}")
        self.pos += 1
        return tok

    def parse(self):
        return self.parse_program()

    def parse_program(self):
        statements = []
        while self.current()['type'] != 'EOF':
            statements.append(self.parse_statement())
        return {'type': 'Program', 'body': statements}

    def parse_statement(self):
        tok = self.current()
        if tok['type'] == 'KEYWORD' and tok['value'] in ('int', 'float', 'string', 'void'):
            # Look ahead for function or var decl
            next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            next_next_tok = self.tokens[self.pos + 2] if self.pos + 2 < len(self.tokens) else None
            
            if next_next_tok and next_next_tok['value'] == '(':
                return self.parse_func_decl()
            else:
                return self.parse_var_decl()
        elif tok['type'] == 'IDENTIFIER':
            # Assignment or function call statement
            next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_tok and next_tok['value'] == '=':
                return self.parse_assignment()
            else:
                expr = self.parse_expr()
                self.consume('DELIMITER', ';')
                return {'type': 'ExprStmt', 'expr': expr}
        elif tok['value'] == 'if':
            return self.parse_if()
        elif tok['value'] == 'while':
            return self.parse_while()
        elif tok['value'] == 'return':
            return self.parse_return()
        else:
            raise CompileError(f"Syntax Error: Unexpected token '{tok['value']}' at line {tok['line']}")

    def parse_var_decl(self):
        vtype = self.consume('KEYWORD')['value']
        name = self.consume('IDENTIFIER')['value']
        init = None
        if self.current()['value'] == '=':
            self.consume('OPERATOR', '=')
            init = self.parse_expr()
        self.consume('DELIMITER', ';')
        return {'type': 'VarDecl', 'varType': vtype, 'name': name, 'init': init}

    def parse_func_decl(self):
        rtype = self.consume('KEYWORD')['value']
        name = self.consume('IDENTIFIER')['value']
        self.consume('DELIMITER', '(')
        params = []
        if self.current()['value'] != ')':
            ptype = self.consume('KEYWORD')['value']
            pname = self.consume('IDENTIFIER')['value']
            params.append({'type': ptype, 'name': pname})
            while self.current()['value'] == ',':
                self.consume('DELIMITER', ',')
                ptype = self.consume('KEYWORD')['value']
                pname = self.consume('IDENTIFIER')['value']
                params.append({'type': ptype, 'name': pname})
        self.consume('DELIMITER', ')')
        body = self.parse_block()
        return {'type': 'FuncDecl', 'returnType': rtype, 'name': name, 'params': params, 'body': body}

    def parse_assignment(self):
        name = self.consume('IDENTIFIER')['value']
        self.consume('OPERATOR', '=')
        expr = self.parse_expr()
        self.consume('DELIMITER', ';')
        return {'type': 'Assignment', 'name': name, 'expr': expr}

    def parse_if(self):
        self.consume('KEYWORD', 'if')
        self.consume('DELIMITER', '(')
        cond = self.parse_expr()
        self.consume('DELIMITER', ')')
        then_branch = self.parse_block()
        else_branch = None
        if self.current()['value'] == 'else':
            self.consume('KEYWORD', 'else')
            else_branch = self.parse_block()
        return {'type': 'IfStmt', 'condition': cond, 'then': then_branch, 'else': else_branch}

    def parse_while(self):
        self.consume('KEYWORD', 'while')
        self.consume('DELIMITER', '(')
        cond = self.parse_expr()
        self.consume('DELIMITER', ')')
        body = self.parse_block()
        return {'type': 'WhileStmt', 'condition': cond, 'body': body}

    def parse_return(self):
        self.consume('KEYWORD', 'return')
        expr = None
        if self.current()['value'] != ';':
            expr = self.parse_expr()
        self.consume('DELIMITER', ';')
        return {'type': 'ReturnStmt', 'expr': expr}

    def parse_block(self):
        self.consume('DELIMITER', '{')
        statements = []
        while self.current()['value'] != '}':
            statements.append(self.parse_statement())
        self.consume('DELIMITER', '}')
        return {'type': 'Block', 'statements': statements}

    def parse_expr(self):
        return self.parse_comparison()

    def parse_comparison(self):
        node = self.parse_addition()
        while self.current()['value'] in ('==', '!=', '<', '>', '<=', '>=', '&&', '||'):
            op = self.consume('OPERATOR')['value']
            right = self.parse_addition()
            node = {'type': 'BinaryOp', 'operator': op, 'left': node, 'right': right}
        return node

    def parse_addition(self):
        node = self.parse_multiplication()
        while self.current()['value'] in ('+', '-'):
            op = self.consume('OPERATOR')['value']
            right = self.parse_multiplication()
            node = {'type': 'BinaryOp', 'operator': op, 'left': node, 'right': right}
        return node

    def parse_multiplication(self):
        node = self.parse_unary()
        while self.current()['value'] in ('*', '/', '%'):
            op = self.consume('OPERATOR')['value']
            right = self.parse_unary()
            node = {'type': 'BinaryOp', 'operator': op, 'left': node, 'right': right}
        return node

    def parse_unary(self):
        if self.current()['value'] in ('-', '!'):
            op = self.consume('OPERATOR' if self.current()['type'] == 'OPERATOR' else 'KEYWORD')['value']
            expr = self.parse_unary()
            return {'type': 'UnaryOp', 'operator': op, 'expr': expr}
        return self.parse_primary()

    def parse_primary(self):
        tok = self.current()
        if tok['type'] == 'NUMBER':
            self.consume('NUMBER')
            return {'type': 'Literal', 'valueType': 'int', 'value': int(tok['value'])}
        elif tok['type'] == 'FLOAT':
            self.consume('FLOAT')
            return {'type': 'Literal', 'valueType': 'float', 'value': float(tok['value'])}
        elif tok['type'] == 'STRING':
            self.consume('STRING')
            return {'type': 'Literal', 'valueType': 'string', 'value': tok['value']}
        elif tok['type'] == 'IDENTIFIER':
            name = self.consume('IDENTIFIER')['value']
            if self.current()['value'] == '(':
                self.consume('DELIMITER', '(')
                args = []
                if self.current()['value'] != ')':
                    args.append(self.parse_expr())
                    while self.current()['value'] == ',':
                        self.consume('DELIMITER', ',')
                        args.append(self.parse_expr())
                self.consume('DELIMITER', ')')
                return {'type': 'FuncCall', 'name': name, 'args': args}
            return {'type': 'Identifier', 'name': name}
        elif tok['value'] == '(':
            self.consume('DELIMITER', '(')
            expr = self.parse_expr()
            self.consume('DELIMITER', ')')
            return expr
        else:
            raise CompileError(f"Syntax Error: Unexpected token '{tok['value']}' in expression at line {tok['line']}")

# --- Phase 3: Semantic Analysis ---
class SemanticAnalyzer:
    def __init__(self, ast):
        self.ast = ast
        self.scopes = [{}] # Stack of symbol tables
        self.errors = []
        self.symbol_table_history = []
        self.current_func_rtype = None

    def push_scope(self):
        self.scopes.append({})
        
    def pop_scope(self):
        self.scopes.pop()

    def declare(self, name, varType, kind='variable'):
        if name in self.scopes[-1]:
            self.errors.append(f"Semantic Error: '{name}' already declared in this scope")
        else:
            self.scopes[-1][name] = {'type': varType, 'kind': kind, 'depth': len(self.scopes)-1}
            self.symbol_table_history.append({'name': name, 'type': varType, 'kind': kind, 'depth': len(self.scopes)-1})

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def analyze(self):
        self.visit(self.ast)
        return self.symbol_table_history, self.errors

    def visit(self, node):
        if not node: return None
        node_type = node.get('type')
        method = getattr(self, f'visit_{node_type}', self.generic_visit)
        return method(node)

    def generic_visit(self, node):
        for key, value in node.items():
            if isinstance(value, dict) and 'type' in value:
                self.visit(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'type' in item:
                        self.visit(item)

    def visit_Program(self, node):
        self.generic_visit(node)

    def visit_VarDecl(self, node):
        if node['init']:
            init_type = self.visit(node['init'])
            if init_type and init_type != node['varType']:
                self.errors.append(f"Semantic Error: Type mismatch in declaration of '{node['name']}', expected {node['varType']} got {init_type}")
        self.declare(node['name'], node['varType'])

    def visit_FuncDecl(self, node):
        self.declare(node['name'], node['returnType'], 'function')
        self.push_scope()
        self.current_func_rtype = node['returnType']
        for param in node['params']:
            self.declare(param['name'], param['type'], 'parameter')
        self.visit(node['body'])
        self.current_func_rtype = None
        self.pop_scope()

    def visit_Block(self, node):
        self.push_scope()
        self.generic_visit(node)
        self.pop_scope()

    def visit_Assignment(self, node):
        var_info = self.lookup(node['name'])
        if not var_info:
            self.errors.append(f"Semantic Error: Undeclared variable '{node['name']}'")
            return None
        expr_type = self.visit(node['expr'])
        if expr_type and expr_type != var_info['type']:
            self.errors.append(f"Semantic Error: Type mismatch in assignment to '{node['name']}', expected {var_info['type']} got {expr_type}")

    def visit_IfStmt(self, node):
        self.visit(node['condition'])
        self.visit(node['then'])
        if node['else']:
            self.visit(node['else'])

    def visit_WhileStmt(self, node):
        self.visit(node['condition'])
        self.visit(node['body'])

    def visit_ReturnStmt(self, node):
        rtype = self.visit(node['expr']) if node['expr'] else 'void'
        if self.current_func_rtype and rtype != self.current_func_rtype:
            self.errors.append(f"Semantic Error: Return type mismatch, expected {self.current_func_rtype} got {rtype}")

    def visit_BinaryOp(self, node):
        left_type = self.visit(node['left'])
        right_type = self.visit(node['right'])
        if left_type and right_type and left_type != right_type:
            self.errors.append(f"Semantic Warning: Binary operation on mixed types {left_type} and {right_type}")
        if node['operator'] in ('==', '!=', '<', '>', '<=', '>=', '&&', '||'):
            return 'int' # boolean essentially
        return left_type

    def visit_UnaryOp(self, node):
        return self.visit(node['expr'])

    def visit_Literal(self, node):
        return node['valueType']

    def visit_Identifier(self, node):
        var_info = self.lookup(node['name'])
        if not var_info:
            self.errors.append(f"Semantic Error: Undeclared variable '{node['name']}'")
            return 'unknown'
        return var_info['type']

    def visit_FuncCall(self, node):
        func_info = self.lookup(node['name'])
        if not func_info or func_info['kind'] != 'function':
            self.errors.append(f"Semantic Error: Undeclared function '{node['name']}'")
            return 'unknown'
        for arg in node['args']:
            self.visit(arg)
        return func_info['type']

    def visit_ExprStmt(self, node):
        self.visit(node['expr'])

# --- Phase 4: Intermediate Code Generation ---
class ICGGenerator:
    def __init__(self, ast):
        self.ast = ast
        self.instructions = []
        self.temp_count = 0
        self.label_count = 0

    def new_temp(self):
        name = f"t{self.temp_count}"
        self.temp_count += 1
        return name

    def new_label(self):
        name = f"L{self.label_count}"
        self.label_count += 1
        return name

    def emit(self, instr):
        self.instructions.append(instr)

    def generate(self):
        self.visit(self.ast)
        return self.instructions

    def visit(self, node):
        if not node: return None
        method = getattr(self, f"visit_{node['type']}", self.generic_visit)
        return method(node)

    def generic_visit(self, node):
        pass

    def visit_Program(self, node):
        for stmt in node['body']:
            self.visit(stmt)

    def visit_VarDecl(self, node):
        if node['init']:
            val = self.visit(node['init'])
            self.emit(f"{node['name']} = {val}")

    def visit_FuncDecl(self, node):
        self.emit(f"label func_{node['name']}")
        for param in node['params']:
            self.emit(f"pop_param {param['name']}")
        self.visit(node['body'])
        if node['returnType'] == 'void':
            self.emit("return")

    def visit_Block(self, node):
        for stmt in node['statements']:
            self.visit(stmt)

    def visit_Assignment(self, node):
        val = self.visit(node['expr'])
        self.emit(f"{node['name']} = {val}")

    def visit_IfStmt(self, node):
        cond = self.visit(node['condition'])
        l_else = self.new_label()
        l_end = self.new_label()
        self.emit(f"if_false {cond} goto {l_else}")
        self.visit(node['then'])
        self.emit(f"goto {l_end}")
        self.emit(f"label {l_else}")
        if node['else']:
            self.visit(node['else'])
        self.emit(f"label {l_end}")

    def visit_WhileStmt(self, node):
        l_start = self.new_label()
        l_end = self.new_label()
        self.emit(f"label {l_start}")
        cond = self.visit(node['condition'])
        self.emit(f"if_false {cond} goto {l_end}")
        self.visit(node['body'])
        self.emit(f"goto {l_start}")
        self.emit(f"label {l_end}")

    def visit_ReturnStmt(self, node):
        if node['expr']:
            val = self.visit(node['expr'])
            self.emit(f"return {val}")
        else:
            self.emit("return")

    def visit_BinaryOp(self, node):
        left = self.visit(node['left'])
        right = self.visit(node['right'])
        t = self.new_temp()
        self.emit(f"{t} = {left} {node['operator']} {right}")
        return t

    def visit_UnaryOp(self, node):
        expr = self.visit(node['expr'])
        t = self.new_temp()
        self.emit(f"{t} = {node['operator']}{expr}")
        return t

    def visit_Literal(self, node):
        if node['valueType'] == 'string':
            return f"{node['value']}"
        return str(node['value'])

    def visit_Identifier(self, node):
        return node['name']

    def visit_FuncCall(self, node):
        args = [self.visit(arg) for arg in node['args']]
        for arg in args:
            self.emit(f"push_param {arg}")
        t = self.new_temp()
        self.emit(f"{t} = call func_{node['name']}, {len(args)}")
        return t
        
    def visit_ExprStmt(self, node):
        self.visit(node['expr'])

# --- Phase 5: Code Optimization ---
class Optimizer:
    def __init__(self, tac):
        self.tac = tac
        
    def optimize(self):
        before = self.tac[:]
        after = self.constant_folding(self.tac)
        after = self.dead_code_elimination(after)
        
        changes = []
        # simple diffing
        import difflib
        matcher = difflib.SequenceMatcher(None, before, after)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                changes.append(f"Replaced {before[i1:i2]} with {after[j1:j2]}")
            elif tag == 'delete':
                changes.append(f"Removed {before[i1:i2]}")
            elif tag == 'insert':
                changes.append(f"Inserted {after[j1:j2]}")

        return before, after, changes

    def constant_folding(self, tac):
        opt = []
        for instr in tac:
            parts = instr.split(' = ')
            if len(parts) == 2:
                left = parts[0]
                right = parts[1]
                # Check if right is purely numbers and operators
                if re.match(r'^[-+*/%<>=!\s\d.]+$', right):
                    try:
                        # DANGEROUS but it's a mini compiler and safe input
                        val = eval(right.replace('||', 'or').replace('&&', 'and'))
                        opt.append(f"{left} = {val}")
                        continue
                    except:
                        pass
            opt.append(instr)
        return opt

    def dead_code_elimination(self, tac):
        # A very basic DCE: remove assignments to temps that are never used
        used = set()
        for instr in tac:
            parts = instr.split(' ')
            for p in parts:
                if p.startswith('t') or p.isalpha():
                    used.add(p.replace(',',''))
                    
        opt = []
        for instr in tac:
            parts = instr.split(' = ')
            if len(parts) == 2:
                target = parts[0].strip()
                if target.startswith('t') and target not in used:
                    # skip
                    continue
            opt.append(instr)
        return opt

# --- Phase 6: Code Generation ---
class CodeGenerator:
    def __init__(self, tac):
        self.tac = tac
        self.asm = []
        
    def generate(self):
        for instr in self.tac:
            self.asm.append(f"; {instr}")
            parts = instr.split(' ')
            if instr.startswith('label '):
                self.asm.append(f"{parts[1]}:")
            elif instr.startswith('goto '):
                self.asm.append(f"    JMP {parts[1]}")
            elif instr.startswith('if_false '):
                # if_false cond goto L
                self.asm.append(f"    CMP {parts[1]}, 0")
                self.asm.append(f"    JE {parts[3]}")
            elif instr.startswith('return '):
                if len(parts) > 1:
                    self.asm.append(f"    MOV R0, {parts[1]}")
                self.asm.append("    RET")
            elif instr.startswith('return'):
                self.asm.append("    RET")
            elif instr.startswith('push_param '):
                self.asm.append(f"    PUSH {parts[1]}")
            elif instr.startswith('pop_param '):
                self.asm.append(f"    POP {parts[1]}")
            elif ' = ' in instr:
                left, right = instr.split(' = ')
                right_parts = right.split(' ')
                if len(right_parts) == 1:
                    self.asm.append(f"    MOV {left}, {right}")
                elif len(right_parts) == 3:
                    op1, op, op2 = right_parts
                    self.asm.append(f"    MOV R1, {op1}")
                    if op == '+': self.asm.append(f"    ADD R1, {op2}")
                    elif op == '-': self.asm.append(f"    SUB R1, {op2}")
                    elif op == '*': self.asm.append(f"    MUL R1, {op2}")
                    elif op == '/': self.asm.append(f"    DIV R1, {op2}")
                    self.asm.append(f"    MOV {left}, R1")
                elif right.startswith('call '):
                    # call func, n
                    func_name = right_parts[1].replace(',', '')
                    self.asm.append(f"    CALL {func_name}")
                    self.asm.append(f"    MOV {left}, R0")
        return self.asm

# --- Main Entry Point ---
def compile_code(source_code):
    result = {
        'success': False,
        'phases': {},
        'errors': []
    }
    
    try:
        # Phase 1
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        result['phases']['lexer'] = {'tokens': tokens}
        
        # Phase 2
        parser = Parser(tokens)
        ast = parser.parse()
        result['phases']['parser'] = {'ast': ast}
        
        # Phase 3
        semantic = SemanticAnalyzer(ast)
        sym_table, sem_errors = semantic.analyze()
        result['phases']['semantic'] = {'symbol_table': sym_table, 'errors': sem_errors}
        if sem_errors and any("Error" in e for e in sem_errors):
            result['errors'].extend(sem_errors)
            # Proceeding anyway for demonstration
            
        # Phase 4
        icg = ICGGenerator(ast)
        tac = icg.generate()
        result['phases']['tac'] = {'instructions': tac}
        
        # Phase 5
        opt = Optimizer(tac)
        before, after, changes = opt.optimize()
        result['phases']['optimization'] = {'before': before, 'after': after, 'changes': changes}
        
        # Phase 6
        codegen = CodeGenerator(after)
        asm = codegen.generate()
        result['phases']['codegen'] = {'instructions': asm}
        
        result['success'] = len(result['errors']) == 0
        
    except CompileError as e:
        result['errors'].append(str(e))
    except Exception as e:
        result['errors'].append(f"Internal Error: {str(e)}")
        
    return result
