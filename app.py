from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from neo4j import GraphDatabase
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a file handler
fh = logging.FileHandler('app.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'd584a5ded027698197372364a94ab6448355a2c3e2306461f97632b0549ddcaf')

# Neo4j connection
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "loudAl@rm15")
driver = GraphDatabase.driver(uri, auth=(user, password))

def get_db():
    return driver.session()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        
        with get_db() as db:
            result = db.run("MERGE (u:User {username: $username}) "
                            "ON CREATE SET u.password = $password "
                            "RETURN u.username", 
                            username=username, password=hashed_password)
            user = result.single()
            
            if user:
                flash('Registration successful. Please log in.')
                return redirect(url_for('login'))
            else:
                flash('Registration failed. Please try again.')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with get_db() as db:
            result = db.run("MATCH (u:User {username: $username}) RETURN u", 
                            username=username)
            user = result.single()
            
            if user and check_password_hash(user['u']['password'], password):
                session['user_id'] = user['u']['username']
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session['user_id'])

@app.route('/scorecard', methods=['GET', 'POST'])
@login_required
def scorecard():
    if request.method == 'POST':
        data = request.json
        with get_db() as db:
            db.run(
                "MATCH (u:User {username: $username}) "
                "CREATE (s:Scorecard {date: $date, realTimeTicketEntry: $realTimeTicketEntry, timesheets: $timesheets, certifications: $certifications, configurations: $configurations})-[:BELONGS_TO]->(u)",
                username=session['user_id'], 
                date=data['date'], 
                realTimeTicketEntry=data['realTimeTicketEntry'],
                timesheets=data['timesheets'],
                certifications=data['certifications'],
                configurations=data['configurations']
            )
        return jsonify({"status": "success"})
    
    # Retrieve scorecard data for GET request
    with get_db() as db:
        result = db.run(
            "MATCH (u:User {username: $username})<-[:BELONGS_TO]-(s:Scorecard) "
            "RETURN s ORDER BY s.date DESC LIMIT 12",
            username=session['user_id']
        )
        scorecard_data = [dict(record['s']) for record in result]
    
    return render_template('scorecard.html', scorecard_data=scorecard_data, username=session['user_id'])
    
    # Retrieve scorecard data for GET request
    with get_db() as db:
        result = db.run(
            "MATCH (u:User {username: $username})<-[:BELONGS_TO]-(s:Scorecard) "
            "RETURN s ORDER BY s.date DESC LIMIT 12",
            username=current_user.username
        )
        scorecard_data = [dict(record['s']) for record in result]
    
    return render_template('scorecard.html', scorecard_data=scorecard_data, username=current_user.username)

@app.route('/rocks', methods=['GET', 'POST'])
@login_required
def rocks():
    if request.method == 'POST':
        data = request.json
        with get_db() as db:
            db.run(
                "MATCH (u:User {username: $username}) "
                "CREATE (r:Rock {description: $description, due_date: $due_date, status: $status})-[:BELONGS_TO]->(u)",
                username=session['user_id'], description=data['description'], due_date=data['due_date'], status=data['status']
            )
        return jsonify({"status": "success"})
    
    # Fetch existing rocks
    with get_db() as db:
        result = db.run(
            "MATCH (u:User {username: $username})<-[:BELONGS_TO]-(r:Rock) "
            "RETURN r.description as description, r.due_date as due_date, r.status as status",
            username=session['user_id']
        )
        rocks = [dict(record) for record in result]
    
    return render_template('rocks.html', rocks=rocks)
@app.route('/update_rock_status', methods=['POST'])
@login_required
def update_rock_status():
    data = request.json
    with get_db() as db:
        db.run(
            "MATCH (u:User {username: $username})<-[:BELONGS_TO]-(r:Rock {description: $description}) "
            "SET r.status = $status",
            username=session['user_id'], description=data['description'], status=data['status']
        )
    return jsonify({"status": "success"})

@app.route('/people', methods=['GET', 'POST'])
@login_required
def people():
    if request.method == 'POST':
        data = request.json
        with get_db() as db:
            db.run(
                "MATCH (u:User {username: $username}) "
                "CREATE (p:PeopleHeadline {date: $date, headline: $headline})-[:BELONGS_TO]->(u)",
                username=session['user_id'], date=data['date'], headline=data['headline']
            )
        return jsonify({"status": "success"})
    
    # Fetch existing headlines
    with get_db() as db:
        result = db.run(
            "MATCH (u:User {username: $username})<-[:BELONGS_TO]-(p:PeopleHeadline) "
            "RETURN p.date AS date, p.headline AS headline "
            "ORDER BY p.date DESC",
            username=session['user_id']
        )
        headlines = [dict(record) for record in result]
    
    return render_template('people.html', headlines=headlines)

@app.route('/todo', methods=['GET', 'POST'])
@login_required
def todo():
    if request.method == 'POST':
        data = request.json
        with get_db() as db:
            db.run(
                "MATCH (u:User {username: $username}) "
                "CREATE (t:ToDo {description: $description, due_date: $due_date, status: $status})-[:BELONGS_TO]->(u)",
                username=session['user_id'], description=data['description'], due_date=data['due_date'], status=data['status']
            )
        return jsonify({"status": "success"})

    # Fetch existing todos
    with get_db() as db:
        result = db.run(
            "MATCH (u:User {username: $username})<-[:BELONGS_TO]-(t:ToDo) "
            "RETURN t.description as description, t.due_date as due_date, t.status as status",
            username=session['user_id']
        )
        todos = [dict(record) for record in result]

    return render_template('todo.html', todos=todos)

@app.route('/update_todo_status', methods=['POST'])
@login_required
def update_todo_status():
    data = request.json
    with get_db() as db:
        db.run(
            "MATCH (u:User {username: $username})<-[:BELONGS_TO]-(t:ToDo {description: $description}) "
            "SET t.status = $status",
            username=session['user_id'], description=data['description'], status=data['status']
        )
    return jsonify({"status": "success"})

@app.route('/ids', methods=['GET', 'POST'])
@login_required
def ids():
    if request.method == 'POST':
        data = request.json
        with get_db() as db:
            db.run(
                "MATCH (u:User {username: $username}) "
                "CREATE (i:IDS {issue: $issue, discussion: $discussion, solution: $solution})-[:BELONGS_TO]->(u)",
                username=session['user_id'], issue=data['issue'], discussion=data['discussion'], solution=data['solution']
            )
        return jsonify({"status": "success"})

    # Fetch existing IDS problems
    with get_db() as db:
        result = db.run(
            "MATCH (u:User {username: $username})<-[:BELONGS_TO]-(i:IDS) "
            "RETURN i.issue as issue, i.discussion as discussion, i.solution as solution",
            username=session['user_id']
        )
        problems = [dict(record) for record in result]

    return render_template('ids.html', problems=problems)


@app.route('/conclude', methods=['GET', 'POST'])
@login_required
def conclude():
    if request.method == 'POST':
        data = request.json
        with get_db() as db:
            db.run(
                "MATCH (u:User {username: $username}) "
                "CREATE (c:Conclude {date: $date, score: $score, notes: $notes})-[:BELONGS_TO]->(u)",
                username=session['user_id'], date=data['date'], score=data['score'], notes=data['notes']
            )
        return jsonify({"status": "success"})
    return render_template('conclude.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)