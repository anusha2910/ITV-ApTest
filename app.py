import os
import csv
import io
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Secret key
app.secret_key = os.environ.get("SESSION_SECRET", "mysecretkey123")
app.config['SECRET_KEY'] = app.secret_key

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload folder
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    wrong_answers = db.Column(db.Integer, nullable=False)
    score_percentage = db.Column(db.Float, nullable=False)
    time_taken = db.Column(db.Integer, default=0)
    answers_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Please login as admin to access this page.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    subjects = db.session.query(Question.subject).distinct().all()
    subjects = [s[0] for s in subjects]
    return render_template('index.html', subjects=subjects)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, is_admin=True).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    questions = Question.query.order_by(Question.created_at.desc()).all()
    subjects = db.session.query(Question.subject).distinct().all()
    subjects = [s[0] for s in subjects]
    stats = {
        'total_questions': Question.query.count(),
        'total_tests': TestResult.query.count(),
        'subjects': len(subjects)
    }
    return render_template('admin_dashboard.html', questions=questions, stats=stats, subjects=subjects)

@app.route('/admin/question/add', methods=['GET', 'POST'])
@admin_required
def add_question():
    if request.method == 'POST':
        question = Question(
            question_text=request.form.get('question_text'),
            option_a=request.form.get('option_a'),
            option_b=request.form.get('option_b'),
            option_c=request.form.get('option_c'),
            option_d=request.form.get('option_d'),
            correct_answer=request.form.get('correct_answer'),
            subject=request.form.get('subject'),
            difficulty=request.form.get('difficulty')
        )
        db.session.add(question)
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_question.html')

@app.route('/admin/question/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_question(id):
    question = Question.query.get_or_404(id)
    if request.method == 'POST':
        question.question_text = request.form.get('question_text')
        question.option_a = request.form.get('option_a')
        question.option_b = request.form.get('option_b')
        question.option_c = request.form.get('option_c')
        question.option_d = request.form.get('option_d')
        question.correct_answer = request.form.get('correct_answer')
        question.subject = request.form.get('subject')
        question.difficulty = request.form.get('difficulty')
        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_question.html', question=question)

@app.route('/admin/question/delete/<int:id>', methods=['POST'])
@admin_required
def delete_question(id):
    question = Question.query.get_or_404(id)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/upload-csv', methods=['GET', 'POST'])
@admin_required
def upload_csv():
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('upload_csv'))
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('upload_csv'))
        
        if file and file.filename.endswith('.csv'):
            try:
                stream = io.StringIO(file.stream.read().decode('UTF-8'), newline=None)
                csv_reader = csv.DictReader(stream)
                count = 0
                for row in csv_reader:
                    question = Question(
                        question_text=row.get('question_text', ''),
                        option_a=row.get('option_a', ''),
                        option_b=row.get('option_b', ''),
                        option_c=row.get('option_c', ''),
                        option_d=row.get('option_d', ''),
                        correct_answer=row.get('correct_answer', '').upper(),
                        subject=row.get('subject', ''),
                        difficulty=row.get('difficulty', 'Medium')
                    )
                    db.session.add(question)
                    count += 1
                db.session.commit()
                flash(f'Successfully uploaded {count} questions!', 'success')
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Please upload a CSV file.', 'error')
        return redirect(url_for('admin_dashboard'))
    return render_template('upload_csv.html')

@app.route('/start-test', methods=['POST'])
def start_test():
    subject = request.form.get('subject')
    difficulty = request.form.get('difficulty')
    num_questions = int(request.form.get('num_questions', 10))
    time_limit = int(request.form.get('time_limit', 10))
    
    query = Question.query.filter_by(subject=subject)
    if difficulty and difficulty != 'All':
        query = query.filter_by(difficulty=difficulty)
    
    questions = query.order_by(db.func.random()).limit(num_questions).all()
    
    if not questions:
        flash('No questions available for the selected criteria.', 'error')
        return redirect(url_for('index'))
    
    session['test_questions'] = [q.id for q in questions]
    session['test_subject'] = subject
    session['test_difficulty'] = difficulty
    session['test_answers'] = {}
    session['test_start_time'] = datetime.utcnow().isoformat()
    session['time_limit'] = time_limit
    
    return redirect(url_for('take_test', question_num=1))

@app.route('/test/<int:question_num>', methods=['GET', 'POST'])
def take_test(question_num):
    if 'test_questions' not in session:
        flash('Please start a new test.', 'error')
        return redirect(url_for('index'))
    
    question_ids = session['test_questions']
    total_questions = len(question_ids)
    
    if question_num < 1 or question_num > total_questions:
        return redirect(url_for('take_test', question_num=1))
    
    if request.method == 'POST':
        answer = request.form.get('answer')
        if answer:
            answers = session.get('test_answers', {})
            answers[str(question_ids[question_num - 1])] = answer
            session['test_answers'] = answers
    
    question = Question.query.get(question_ids[question_num - 1])
    current_answer = session.get('test_answers', {}).get(str(question.id))
    
    start_time = datetime.fromisoformat(session['test_start_time'])
    elapsed = (datetime.utcnow() - start_time).total_seconds()
    time_limit_seconds = session.get('time_limit', 10) * 60
    remaining_time = max(0, time_limit_seconds - elapsed)
    
    return render_template('take_test.html',
                         question=question,
                         question_num=question_num,
                         total_questions=total_questions,
                         current_answer=None,
                         remaining_time=int(remaining_time),
                         time_limit=session.get('time_limit', 10))

@app.route('/test/save-answer', methods=['POST'])
def save_answer():
    if 'test_questions' not in session:
        return jsonify({'success': False, 'error': 'No active test'})
    
    data = request.get_json()
    question_id = data.get('question_id')
    answer = data.get('answer')
    
    if question_id and answer:
        answers = session.get('test_answers', {})
        answers[str(question_id)] = answer
        session['test_answers'] = answers
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@app.route('/submit-test', methods=['POST'])
def submit_test():
    if 'test_questions' not in session:
        flash('No active test to submit.', 'error')
        return redirect(url_for('index'))
    
    question_ids = session['test_questions']
    answers = session.get('test_answers', {})
    subject = session.get('test_subject')
    difficulty = session.get('test_difficulty')
    
    start_time = datetime.fromisoformat(session['test_start_time'])
    time_taken = int((datetime.utcnow() - start_time).total_seconds())
    
    correct = 0
    wrong = 0
    review_data = []
    
    for qid in question_ids:
        question = Question.query.get(qid)
        user_answer = answers.get(str(qid), '')
        is_correct = user_answer.upper() == question.correct_answer.upper()
        
        if user_answer:
            if is_correct:
                correct += 1
            else:
                wrong += 1
        
        review_data.append({
            'id': qid,
            'question_text': question.question_text,
            'option_a': question.option_a,
            'option_b': question.option_b,
            'option_c': question.option_c,
            'option_d': question.option_d,
            'correct_answer': question.correct_answer,
            'user_answer': user_answer,
            'is_correct': is_correct
        })
    
    total = len(question_ids)
    score_percentage = (correct / total * 100) if total > 0 else 0
    
    result = TestResult(
        subject=subject,
        difficulty=difficulty or 'All',
        total_questions=total,
        correct_answers=correct,
        wrong_answers=wrong,
        score_percentage=score_percentage,
        time_taken=time_taken,
        answers_data=str(review_data)
    )
    db.session.add(result)
    db.session.commit()
    
    session['last_result'] = {
        'id': result.id,
        'subject': subject,
        'difficulty': difficulty,
        'total': total,
        'correct': correct,
        'wrong': wrong,
        'unanswered': total - correct - wrong,
        'score': round(score_percentage, 1),
        'time_taken': time_taken,
        'review_data': review_data
    }
    
    session.pop('test_questions', None)
    session.pop('test_answers', None)
    session.pop('test_subject', None)
    session.pop('test_difficulty', None)
    session.pop('test_start_time', None)
    session.pop('time_limit', None)
    
    return redirect(url_for('show_result'))

@app.route('/result')
def show_result():
    result = session.get('last_result')
    if not result:
        flash('No test result available.', 'error')
        return redirect(url_for('index'))
    return render_template('result.html', result=result)

@app.route('/review')
def review_answers():
    result = session.get('last_result')
    if not result:
        flash('No test result available for review.', 'error')
        return redirect(url_for('index'))
    return render_template('review.html', result=result)

@app.route('/api/questions/<subject>')
def get_question_count(subject):
    difficulties = ['Easy', 'Medium', 'Hard']
    counts = {}
    for diff in difficulties:
        counts[diff] = Question.query.filter_by(subject=subject, difficulty=diff).count()
    counts['All'] = Question.query.filter_by(subject=subject).count()
    return jsonify(counts)

def init_db():
    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: username='admin', password='admin123'")
        
        if Question.query.count() == 0:
            sample_questions = [
                # Aptitude Questions
                {"question_text": "If a train travels 360 km in 4 hours, what is its speed?", "option_a": "80 km/h", "option_b": "90 km/h", "option_c": "100 km/h", "option_d": "70 km/h", "correct_answer": "B", "subject": "Aptitude", "difficulty": "Easy"},
                {"question_text": "A shopkeeper sells an item for Rs. 450 at a profit of 25%. What was the cost price?", "option_a": "Rs. 350", "option_b": "Rs. 360", "option_c": "Rs. 375", "option_d": "Rs. 400", "correct_answer": "B", "subject": "Aptitude", "difficulty": "Medium"},
                {"question_text": "If 5 workers can complete a job in 12 days, how many days will 10 workers take?", "option_a": "6 days", "option_b": "8 days", "option_c": "10 days", "option_d": "24 days", "correct_answer": "A", "subject": "Aptitude", "difficulty": "Easy"},
                {"question_text": "What is the compound interest on Rs. 10,000 at 10% per annum for 2 years?", "option_a": "Rs. 2,000", "option_b": "Rs. 2,100", "option_c": "Rs. 2,200", "option_d": "Rs. 1,900", "correct_answer": "B", "subject": "Aptitude", "difficulty": "Medium"},
                {"question_text": "A and B together can complete a work in 12 days. A alone can do it in 20 days. In how many days can B alone complete the work?", "option_a": "25 days", "option_b": "30 days", "option_c": "35 days", "option_d": "40 days", "correct_answer": "B", "subject": "Aptitude", "difficulty": "Hard"},
                {"question_text": "The average of 5 numbers is 20. If one number is excluded, the average becomes 18. What is the excluded number?", "option_a": "24", "option_b": "26", "option_c": "28", "option_d": "30", "correct_answer": "C", "subject": "Aptitude", "difficulty": "Medium"},
                {"question_text": "A car covers a distance of 150 km in 2.5 hours. What is the average speed?", "option_a": "50 km/h", "option_b": "55 km/h", "option_c": "60 km/h", "option_d": "65 km/h", "correct_answer": "C", "subject": "Aptitude", "difficulty": "Easy"},
                {"question_text": "If the ratio of two numbers is 3:5 and their sum is 64, find the smaller number.", "option_a": "20", "option_b": "24", "option_c": "28", "option_d": "32", "correct_answer": "B", "subject": "Aptitude", "difficulty": "Easy"},
                
                # Logical Reasoning Questions
                {"question_text": "If FRIEND is coded as HUMJTK, how is CANDLE coded?", "option_a": "EDRIRL", "option_b": "DCPFNG", "option_c": "ESJFME", "option_d": "FYOBKC", "correct_answer": "A", "subject": "Logical Reasoning", "difficulty": "Medium"},
                {"question_text": "Complete the series: 2, 6, 12, 20, 30, ?", "option_a": "40", "option_b": "42", "option_c": "44", "option_d": "46", "correct_answer": "B", "subject": "Logical Reasoning", "difficulty": "Easy"},
                {"question_text": "If A is the brother of B, B is the sister of C, and C is the father of D, how is A related to D?", "option_a": "Uncle", "option_b": "Father", "option_c": "Grandfather", "option_d": "Brother", "correct_answer": "A", "subject": "Logical Reasoning", "difficulty": "Medium"},
                {"question_text": "Which number should come next in the series: 1, 4, 9, 16, 25, ?", "option_a": "30", "option_b": "36", "option_c": "49", "option_d": "64", "correct_answer": "B", "subject": "Logical Reasoning", "difficulty": "Easy"},
                {"question_text": "All roses are flowers. Some flowers fade quickly. Conclusion: Some roses fade quickly.", "option_a": "Definitely True", "option_b": "Definitely False", "option_c": "Probably True", "option_d": "Cannot be determined", "correct_answer": "D", "subject": "Logical Reasoning", "difficulty": "Hard"},
                {"question_text": "Point A is 10 km north of B. C is 5 km east of A. What is the direction of C from B?", "option_a": "North-East", "option_b": "North-West", "option_c": "South-East", "option_d": "South-West", "correct_answer": "A", "subject": "Logical Reasoning", "difficulty": "Medium"},
                {"question_text": "If Monday falls on 1st of a month, what day falls on 25th?", "option_a": "Tuesday", "option_b": "Wednesday", "option_c": "Thursday", "option_d": "Friday", "correct_answer": "C", "subject": "Logical Reasoning", "difficulty": "Easy"},
                {"question_text": "Find the odd one out: 3, 5, 11, 14, 17, 21", "option_a": "21", "option_b": "14", "option_c": "5", "option_d": "3", "correct_answer": "B", "subject": "Logical Reasoning", "difficulty": "Medium"},
                
                # English Grammar Questions
                {"question_text": "Choose the correct form: She ___ to the market yesterday.", "option_a": "go", "option_b": "goes", "option_c": "went", "option_d": "gone", "correct_answer": "C", "subject": "English Grammar", "difficulty": "Easy"},
                {"question_text": "Identify the error: 'He gave me a advice about my career.'", "option_a": "He", "option_b": "a advice", "option_c": "about", "option_d": "career", "correct_answer": "B", "subject": "English Grammar", "difficulty": "Easy"},
                {"question_text": "Choose the synonym of 'Abundant':", "option_a": "Scarce", "option_b": "Plentiful", "option_c": "Limited", "option_d": "Rare", "correct_answer": "B", "subject": "English Grammar", "difficulty": "Medium"},
                {"question_text": "The antonym of 'Benevolent' is:", "option_a": "Kind", "option_b": "Generous", "option_c": "Malevolent", "option_d": "Caring", "correct_answer": "C", "subject": "English Grammar", "difficulty": "Medium"},
                {"question_text": "Choose the correct sentence:", "option_a": "He don't know nothing", "option_b": "He doesn't knows anything", "option_c": "He doesn't know anything", "option_d": "He don't knows nothing", "correct_answer": "C", "subject": "English Grammar", "difficulty": "Easy"},
                {"question_text": "The word 'Ubiquitous' means:", "option_a": "Rare", "option_b": "Present everywhere", "option_c": "Ancient", "option_d": "Modern", "correct_answer": "B", "subject": "English Grammar", "difficulty": "Hard"},
                {"question_text": "Choose the correct preposition: She is good ___ mathematics.", "option_a": "in", "option_b": "at", "option_c": "on", "option_d": "with", "correct_answer": "B", "subject": "English Grammar", "difficulty": "Easy"},
                {"question_text": "The passive voice of 'They are building a house' is:", "option_a": "A house is built by them", "option_b": "A house is being built by them", "option_c": "A house was being built by them", "option_d": "A house has been built by them", "correct_answer": "B", "subject": "English Grammar", "difficulty": "Medium"},
                
                # General Knowledge Questions
                {"question_text": "Which planet is known as the Red Planet?", "option_a": "Venus", "option_b": "Mars", "option_c": "Jupiter", "option_d": "Saturn", "correct_answer": "B", "subject": "General Knowledge", "difficulty": "Easy"},
                {"question_text": "Who invented the telephone?", "option_a": "Thomas Edison", "option_b": "Nikola Tesla", "option_c": "Alexander Graham Bell", "option_d": "Guglielmo Marconi", "correct_answer": "C", "subject": "General Knowledge", "difficulty": "Easy"},
                {"question_text": "What is the capital of Australia?", "option_a": "Sydney", "option_b": "Melbourne", "option_c": "Canberra", "option_d": "Perth", "correct_answer": "C", "subject": "General Knowledge", "difficulty": "Medium"},
                {"question_text": "Which gas is most abundant in Earth's atmosphere?", "option_a": "Oxygen", "option_b": "Carbon Dioxide", "option_c": "Nitrogen", "option_d": "Hydrogen", "correct_answer": "C", "subject": "General Knowledge", "difficulty": "Easy"},
                {"question_text": "The currency of Japan is:", "option_a": "Yuan", "option_b": "Won", "option_c": "Yen", "option_d": "Ringgit", "correct_answer": "C", "subject": "General Knowledge", "difficulty": "Easy"},
                {"question_text": "Which is the largest ocean in the world?", "option_a": "Atlantic Ocean", "option_b": "Indian Ocean", "option_c": "Arctic Ocean", "option_d": "Pacific Ocean", "correct_answer": "D", "subject": "General Knowledge", "difficulty": "Easy"},
                {"question_text": "Who wrote 'Romeo and Juliet'?", "option_a": "Charles Dickens", "option_b": "William Shakespeare", "option_c": "Jane Austen", "option_d": "Mark Twain", "correct_answer": "B", "subject": "General Knowledge", "difficulty": "Easy"},
                {"question_text": "What is the chemical symbol for Gold?", "option_a": "Ag", "option_b": "Au", "option_c": "Fe", "option_d": "Cu", "correct_answer": "B", "subject": "General Knowledge", "difficulty": "Medium"},
                
                # Verbal Ability Questions
                {"question_text": "Choose the word that best completes the analogy: Book : Reading :: Fork : ?", "option_a": "Writing", "option_b": "Eating", "option_c": "Drawing", "option_d": "Sleeping", "correct_answer": "B", "subject": "Verbal Ability", "difficulty": "Easy"},
                {"question_text": "Find the correctly spelled word:", "option_a": "Accomodation", "option_b": "Accommodation", "option_c": "Acommodation", "option_d": "Acomodation", "correct_answer": "B", "subject": "Verbal Ability", "difficulty": "Medium"},
                {"question_text": "Choose the word most similar in meaning to 'Eloquent':", "option_a": "Silent", "option_b": "Articulate", "option_c": "Quiet", "option_d": "Reserved", "correct_answer": "B", "subject": "Verbal Ability", "difficulty": "Medium"},
                {"question_text": "What is the meaning of the idiom 'A piece of cake'?", "option_a": "Something delicious", "option_b": "Something very easy", "option_c": "A small portion", "option_d": "A celebration", "correct_answer": "B", "subject": "Verbal Ability", "difficulty": "Easy"},
                {"question_text": "Choose the word opposite in meaning to 'Transparent':", "option_a": "Clear", "option_b": "Obvious", "option_c": "Opaque", "option_d": "Visible", "correct_answer": "C", "subject": "Verbal Ability", "difficulty": "Medium"},
                {"question_text": "Identify the correctly punctuated sentence:", "option_a": "Its a beautiful day isnt it", "option_b": "Its a beautiful day, isn't it?", "option_c": "It's a beautiful day, isn't it?", "option_d": "Its a beautiful day isn't it?", "correct_answer": "C", "subject": "Verbal Ability", "difficulty": "Medium"},
                {"question_text": "Choose the correct meaning of 'Ephemeral':", "option_a": "Lasting forever", "option_b": "Short-lived", "option_c": "Very old", "option_d": "Extremely large", "correct_answer": "B", "subject": "Verbal Ability", "difficulty": "Hard"},
                {"question_text": "Which sentence uses the word 'their' correctly?", "option_a": "Their going to the park", "option_b": "They put there books on the table", "option_c": "The students finished their homework", "option_d": "There car is parked outside", "correct_answer": "C", "subject": "Verbal Ability", "difficulty": "Easy"},
            ]
            
            for q_data in sample_questions:
                question = Question(**q_data)
                db.session.add(question)
            
            db.session.commit()
            print(f"Added {len(sample_questions)} sample questions.")

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
