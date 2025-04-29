from flask import Flask, request, render_template
from scoring_module import comprehensive_score  # 导入综合评分函数

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/score', methods=['POST'])
def score():
    paper_text = request.form.get('paper_content', '')
    score_details = comprehensive_score(paper_text)  # 获取详细评分
    return render_template('result.html', details=score_details)

if __name__ == '__main__':
    app.run(debug=True)