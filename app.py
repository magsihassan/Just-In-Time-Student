from flask import Flask, request, jsonify, render_template
from compiler import compile_code

app = Flask(__name__)

# Sample programs
SAMPLES = {
    'arithmetic': """int main() {
    int a = 10;
    int b = 20;
    int c = a + b * 2;
    return c;
}""",
    'factorial': """int factorial(int n) {
    if (n <= 1) {
        return 1;
    } else {
        return n * factorial(n - 1);
    }
}

int main() {
    return factorial(5);
}""",
    'fibonacci': """int main() {
    int n = 10;
    int a = 0;
    int b = 1;
    int temp = 0;
    int i = 0;
    
    while (i < n) {
        temp = a + b;
        a = b;
        b = temp;
        i = i + 1;
    }
    
    return b;
}""",
    'max': """int max(int a, int b) {
    if (a > b) {
        return a;
    } else {
        return b;
    }
}

int main() {
    return max(42, 100);
}"""
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compile', methods=['POST'])
def compile_endpoint():
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'error': 'No code provided'}), 400
        
    code = data['code']
    result = compile_code(code)
    return jsonify(result)

@app.route('/samples/<name>')
def get_sample(name):
    if name in SAMPLES:
        return jsonify({'code': SAMPLES[name]})
    return jsonify({'error': 'Sample not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
